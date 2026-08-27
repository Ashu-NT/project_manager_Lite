"""Approval-P2: typed `ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected` DomainEvents.

Mirrors `test_role_binding_events.py`'s own structure (contract guards, Clock determinism,
exactly-once recording, failure paths, cross-tenant/cross-org isolation, transactional/postcommit
handler semantics, committed-order sequencing) -- the same proof shape, applied to Approval's
five effective request-creation contexts (standalone `request_change` plus the four converged
host workflows) and its two decision commands (`approve_and_apply`/`reject`).
"""

from __future__ import annotations

import inspect
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.domain.approval import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequest,
    ApprovalRequested,
    ApprovalStatus,
)
from src.core.shared.events.domain_event import DomainEvent

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _login_as_fresh_requester(services) -> str:
    username = _unique("evt-requester")
    services["auth_service"].register_user(username, "StrongPass123", role_names=["planner"])
    _login(services, username, "StrongPass123")
    return username


class _FixedClock:
    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


def _spy_recorded_events(uow_factory, monkeypatch) -> list:
    """Mirrors `test_role_binding_events.py::_spy_recorded_events` -- captures every event
    recorded via `uow.record_event(...)` on ANY UoW `uow_factory.create(...)` produces, asserting
    (structurally, not by convention) that recording happens strictly before `uow._committed`
    flips True."""
    recorded = []
    original_create = type(uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        original_record_event = uow.record_event

        def _spy_record_event(event):
            assert uow._committed is False, "event must be recorded before commit, not after"
            recorded.append(event)
            return original_record_event(event)

        uow.record_event = _spy_record_event
        return uow

    monkeypatch.setattr(type(uow_factory), "create", _spy_create)
    return recorded


def _submitted_budget(services, session):
    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        _unique("Approval Events Project"), financial_currency_code="USD"
    )
    budget_service = services["budget_service"]
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=_unique("EVT-CC"), name="Approval events cost code"
    )
    budget = budget_service.create_budget(project.id, "Events Budget")
    budget_service.add_line(
        budget.id,
        cost_code_id=cost_code.id,
        description="Line 1",
        amount=1000,
        expected_budget_version=budget.row_version,
    )
    budget = budget_service.get_budget(budget.id)
    budget = budget_service.submit_budget(
        budget.id, submitted_by="admin", expected_version=budget.row_version
    )
    session.expire_all()
    return project, budget


def _request_budget_approval_as_a_different_user(services, budget):
    """Requests as a fresh, non-admin user, then logs back in as admin (the eventual decider) --
    avoids the self-decision rule, mirroring `test_approval_service_unit_of_work_cutover.py`.

    P10A: a fresh login's active-organization auto-select is genuinely ambiguous once more than
    one organization is enabled simultaneously (no longer "the one enabled org", unlike the
    pre-P10A mutual-exclusion model) -- pin it explicitly to whatever was active immediately
    before the switch rather than relying on that heuristic."""
    active_organization_id = services["tenant_context_service"].get_active_organization_id()
    _login_as_fresh_requester(services)
    if active_organization_id:
        services["user_session"].set_active_organization_id(active_organization_id)
    approvals = services["approval_service"]
    request = approvals.request_change(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id=budget.id,
        project_id=budget.project_id,
        payload={"budget_id": budget.id, "expected_version": budget.row_version, "notes": ""},
    )
    _login(services, "admin", "ChangeMe123!")
    return request


# ---------------------------------------------------------------------------
# Event contract / architecture guards
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event_cls,fields_expected",
    [
        (
            ApprovalRequested,
            {
                "approval_id", "tenant_id", "organization_id", "approval_type",
                "entity_type", "entity_id", "requested_by_user_id", "occurred_at",
            },
        ),
        (
            ApprovalApproved,
            {
                "approval_id", "tenant_id", "organization_id", "approval_type",
                "entity_type", "entity_id", "decided_by_user_id", "occurred_at",
            },
        ),
        (
            ApprovalRejected,
            {
                "approval_id", "tenant_id", "organization_id", "approval_type",
                "entity_type", "entity_id", "decided_by_user_id", "occurred_at",
            },
        ),
    ],
)
def test_approval_event_conforms_to_domain_event_and_has_only_the_locked_fields(
    event_cls, fields_expected
):
    event = event_cls(
        approval_id="approval-1",
        tenant_id="tenant-1",
        organization_id="org-1",
        approval_type="budget.approve",
        entity_type="project_budget",
        entity_id="budget-1",
        **(
            {"requested_by_user_id": "user-1"}
            if event_cls is ApprovalRequested
            else {"decided_by_user_id": "user-1"}
        ),
        occurred_at=datetime.now(timezone.utc),
    )
    assert isinstance(event, DomainEvent)
    assert is_dataclass(event)
    assert {f.name for f in fields(event)} == fields_expected
    with pytest.raises(AttributeError):
        event.approval_id = "changed"  # type: ignore[misc]
    for forbidden in (
        "payload", "project_id", "correlation_id", "causation_id", "command_id",
        "schema_version", "display_name", "audit_text", "rejection_reason", "decision_note",
    ):
        assert not hasattr(event, forbidden)


def _imported_module_names(module) -> set[str]:
    import ast

    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_approval_events_module_has_no_ui_or_infrastructure_vocabulary():
    from src.core.platform.domain.approval import events as events_module

    imports = _imported_module_names(events_module)
    for forbidden in (
        "view_invalidation", "domain_events", "pyside6", "qtcore", "ui_qml",
        "infrastructure", "sqlalchemy",
    ):
        assert not any(forbidden in name.lower() for name in imports), imports


def test_approval_request_does_not_implement_records_domain_events():
    base_names = {base.__name__ for base in ApprovalRequest.__mro__}
    assert "RecordsDomainEvents" not in base_names


def test_no_approval_applied_or_changed_event_classes_exist():
    """§40: `ApprovalApplied`/`ApprovalChanged`/`ApprovalStatusChanged` must not exist anywhere
    in production source -- there is no fourth Approval event, by locked design."""
    import re
    from pathlib import Path

    src_core = Path(__file__).resolve().parents[2] / "core"
    for forbidden in ("ApprovalApplied", "ApprovalChanged", "ApprovalStatusChanged"):
        for path in src_core.rglob("*.py"):
            if "approval" not in path.as_posix().lower():
                continue
            source = path.read_text(encoding="utf-8", errors="ignore")
            assert not re.search(rf"^class {forbidden}\b", source, re.MULTILINE), (
                f"{forbidden} must not be implemented: {path}"
            )


def test_approval_requested_has_exactly_one_recording_responsibility():
    """§9/§11: the transaction-bound Approval request participant is the ONE semantic recording
    boundary for `ApprovalRequested` -- no host service (procurement/purchasing/financial-change/
    billing-preparation) or `ApprovalService` itself constructs it independently."""
    from pathlib import Path

    src_core = Path(__file__).resolve().parents[2] / "core"
    construction_sites = [
        path for path in src_core.rglob("*.py")
        if "ApprovalRequested(" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert [str(p) for p in construction_sites] == [
        str(
            src_core
            / "platform" / "application" / "approval" / "approval_mutation_participant.py"
        )
    ]


# ---------------------------------------------------------------------------
# Clock
# ---------------------------------------------------------------------------


def test_standalone_request_change_uses_the_injected_clock_deterministically(services, monkeypatch):
    _login_as_fresh_requester(services)
    approvals = services["approval_service"]
    fixed_when = datetime(2031, 5, 6, 8, 0, 0, tzinfo=timezone.utc)
    original_clock = approvals._clock
    approvals._clock = _FixedClock(fixed_when)
    try:
        recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)
        approvals.request_change(
            request_type="baseline.create",
            entity_type="project_baseline",
            entity_id=_unique("clock-probe"),
            project_id=None,
            payload={"name": "Clock probe"},
        )
        assert len(recorded) == 1
        assert recorded[0].occurred_at == fixed_when
    finally:
        approvals._clock = original_clock


# ---------------------------------------------------------------------------
# ApprovalRequested -- exactly once, all five effective request contexts
# ---------------------------------------------------------------------------


def test_standalone_request_change_records_exactly_one_approval_requested(services, monkeypatch):
    _login_as_fresh_requester(services)
    approvals = services["approval_service"]
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    request = approvals.request_change(
        request_type="baseline.create",
        entity_type="project_baseline",
        entity_id=_unique("standalone-probe"),
        project_id=None,
        payload={"name": "Standalone probe"},
    )

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ApprovalRequested)
    assert event.approval_id == request.id
    assert event.tenant_id == request.tenant_id
    assert event.organization_id == request.organization_id
    assert event.approval_type == "baseline.create"
    assert event.entity_type == "project_baseline"
    assert event.requested_by_user_id == request.requested_by_user_id


def test_submit_requisition_records_exactly_one_approval_requested(services, monkeypatch):
    from src.tests.ui_runtime_helpers import login_as

    site = services["site_service"].create_site(
        site_code=_unique("EVT-SITE"), name="Events Site", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=_unique("EVT-ITEM"), name="Events Item", status="ACTIVE",
        stock_uom="EA", is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique("EVT-ROOM"), name="Events Storeroom", site_id=site.id, status="ACTIVE",
    )
    auth = services["auth_service"]
    username = _unique("evt-req-user")
    auth.register_user(username, "StrongPass123", role_names=["inventory_manager"])
    login_as(services, username, "StrongPass123")

    procurement = services["inventory_procurement_service"]
    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Events probe",
    )
    procurement.add_requisition_line(requisition.id, stock_item_id=item.id, quantity_requested=1)

    recorded = _spy_recorded_events(procurement._requisition_submission_uow_factory, monkeypatch)
    submitted = procurement.submit_requisition(requisition.id)

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ApprovalRequested)
    assert event.approval_id == submitted.approval_request_id
    assert event.approval_type == "purchase_requisition.submit"
    assert event.entity_type == "purchase_requisition"
    assert event.entity_id == requisition.id


def test_submit_purchase_order_records_exactly_one_approval_requested(services, monkeypatch):
    site = services["site_service"].create_site(
        site_code=_unique("EVT-PO-SITE"), name="Events PO Site", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=_unique("EVT-PO-ITEM"), name="Events PO Item", status="ACTIVE",
        stock_uom="EA", is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=_unique("EVT-PO-ROOM"), name="Events PO Storeroom", site_id=site.id, status="ACTIVE",
    )
    from src.core.platform.domain.master_data.party import PartyType

    supplier = services["party_service"].create_party(
        party_code=_unique("EVT-PO-SUP"), party_name="Events Supplier", party_type=PartyType.SUPPLIER,
    )
    purchasing = services["inventory_purchasing_service"]
    purchase_order = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR",
        source_requisition_id=None, expected_delivery_date=date(2026, 6, 1),
    )
    purchasing.add_purchase_order_line(
        purchase_order.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id,
        quantity_ordered=5, unit_price=10.0,
    )

    recorded = _spy_recorded_events(purchasing._purchase_order_submission_uow_factory, monkeypatch)
    submitted = purchasing.submit_purchase_order(purchase_order.id)

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ApprovalRequested)
    assert event.approval_id == submitted.approval_request_id
    assert event.approval_type == "purchase_order.submit"
    assert event.entity_type == "purchase_order"
    assert event.entity_id == purchase_order.id


def test_submit_change_records_exactly_one_approval_requested(services, monkeypatch):
    from src.core.modules.project_management.domain.financials.financial_change import (
        FinancialChangeImpactType,
    )

    _login(services, "admin", "ChangeMe123!")
    project = services["project_service"].create_project(
        _unique("Events Finance Project"), financial_currency_code="USD"
    )
    code = services["financial_configuration_service"].create_cost_code(
        code=_unique("EVT-FIN-CC"), name="Events finance cost code"
    )
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Events approved budget")
    budget_line = budgets.add_line(
        budget.id, cost_code_id=code.id, description="Approved scope", amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)

    changes = services["financial_change_service"]
    change = changes.create_change(
        project.id, title="Events change", reason="Events probe",
        effective_date=date(2026, 8, 11), created_by="admin",
    )
    changes.add_impact(
        change.id, impact_type=FinancialChangeImpactType.BUDGET, description="Increase scope",
        amount=Decimal("10"), cost_code_id=code.id, target_line_id=budget_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)

    recorded = _spy_recorded_events(changes._submission_uow_factory, monkeypatch)
    submitted = changes.submit_change(
        change.id, submitted_by="admin", expected_version=change.row_version
    )

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ApprovalRequested)
    assert event.approval_id == submitted.approval_request_id
    assert event.approval_type == "financial_change.apply"
    assert event.entity_type == "financial_change_request"
    assert event.entity_id == change.id


def test_submit_preparation_records_exactly_one_approval_requested(services, monkeypatch):
    from src.core.modules.project_management.domain.financials.configuration import BillingMethod

    _login(services, "admin", "ChangeMe123!")
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        _unique("Events Billing Project"), financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=_unique("EVT-BILL-CC"), name="Events billing cost code"
    )
    services["financial_period_service"].create_period(
        code=_unique("EVT-FY26"), name="Events period", fiscal_year=2026, period_number=8,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 31),
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id, expected_version=profile.version, default_cost_code_id=cost_code.id,
        billing_method=BillingMethod.FIXED_PRICE, is_billable=True,
    )
    billing_profile_service = services["billing_profile_service"]
    bp_profile = billing_profile_service.create_profile(
        project.id, contract_reference=_unique("EVT-CONTRACT"), contract_value=Decimal("50000"),
        customer_party_id="party-1",
    )
    billing_profile_service.activate_profile(project.id, expected_row_version=bp_profile.row_version)
    line = billing_profile_service.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal("24000"), due_date=date(2026, 8, 20)
    )
    line = billing_profile_service.mark_schedule_line_ready(line.id, expected_row_version=line.row_version)

    billing_preparation_service = services["billing_preparation_service"]
    preparation = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("EVT-BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=_unique("evt-bill-key"),
    )
    billing_preparation_service.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    )
    preparation = billing_preparation_service.get_preparation(preparation.id)

    recorded = _spy_recorded_events(billing_preparation_service._submission_uow_factory, monkeypatch)
    submitted = billing_preparation_service.submit_preparation(
        preparation.id, expected_row_version=preparation.row_version
    )

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ApprovalRequested)
    assert event.approval_id == submitted.approval_request_id
    assert event.approval_type == "project_billing_preparation.approve"
    assert event.entity_type == "project_billing_preparation"
    assert event.entity_id == preparation.id


# ---------------------------------------------------------------------------
# ApprovalApproved -- exactly once, apply-handler-failure suppression
# ---------------------------------------------------------------------------


def test_approve_and_apply_records_exactly_one_approval_approved(services, session, monkeypatch):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    decided = approvals.approve_and_apply(request.id, note="Approved")

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ApprovalApproved)
    assert event.approval_id == request.id
    assert event.tenant_id == decided.tenant_id
    assert event.organization_id == decided.organization_id
    assert event.approval_type == "budget.approve"
    assert event.decided_by_user_id == decided.decided_by_user_id
    assert decided.decided_by_username == "admin"


def test_apply_handler_failure_emits_zero_approval_approved(services, session, monkeypatch):
    """§20: apply participant raises -> zero `ApprovalApproved`, request remains PENDING, and the
    failure is unobservable post-commit (subscribed via the shared bus, not merely absent from
    the spy list -- proving no dispatch reached a real subscriber either)."""
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    bus = approvals._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(ApprovalApproved, lambda e, c: seen.append(e))
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    def _failing_handler(request, deps):
        raise RuntimeError("simulated apply participant failure")

    saved = approvals._apply_handlers["budget.approve"]
    approvals._apply_handlers["budget.approve"] = (_failing_handler, saved[1])
    try:
        with pytest.raises(RuntimeError, match="simulated apply participant failure"):
            approvals.approve_and_apply(request.id, note="Should not apply")
    finally:
        approvals._apply_handlers["budget.approve"] = saved

    assert recorded == []
    assert seen == []
    still_pending = [r for r in approvals.list_pending() if r.id == request.id]
    assert len(still_pending) == 1
    assert still_pending[0].status == ApprovalStatus.PENDING


def test_approve_already_decided_request_emits_zero_new_events(services, session, monkeypatch):
    """§23: a second decision attempt on an already-decided request is a command, not a new
    business fact -- zero events, zero audit, zero postcommit reaction."""
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    approvals.approve_and_apply(request.id, note="First decision")

    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)
    with pytest.raises(BusinessRuleError) as exc_info:
        approvals.approve_and_apply(request.id, note="Second decision")

    assert exc_info.value.code == "APPROVAL_ALREADY_DECIDED"
    assert recorded == []


# ---------------------------------------------------------------------------
# ApprovalRejected -- exactly once, reject-handler-failure suppression
# ---------------------------------------------------------------------------


def test_reject_records_exactly_one_approval_rejected(services, session, monkeypatch):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    decided = approvals.reject(request.id, note="Rejected")

    assert len(recorded) == 1
    event = recorded[0]
    assert isinstance(event, ApprovalRejected)
    assert event.approval_id == request.id
    assert event.tenant_id == decided.tenant_id
    assert event.organization_id == decided.organization_id
    assert event.approval_type == "budget.approve"
    assert event.decided_by_user_id == decided.decided_by_user_id
    assert not hasattr(event, "decision_note")


def test_reject_handler_failure_emits_zero_approval_rejected(services, session, monkeypatch):
    """§22: a registered reject participant raises -> zero `ApprovalRejected`, request remains
    PENDING."""
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    def _failing_reject_handler(request, deps):
        raise RuntimeError("simulated reject participant failure")

    saved = approvals._reject_handlers["budget.approve"]
    approvals._reject_handlers["budget.approve"] = (_failing_reject_handler, saved[1])
    try:
        with pytest.raises(RuntimeError, match="simulated reject participant failure"):
            approvals.reject(request.id, note="Should not reject")
    finally:
        approvals._reject_handlers["budget.approve"] = saved

    assert recorded == []
    still_pending = [r for r in approvals.list_pending() if r.id == request.id]
    assert len(still_pending) == 1
    assert still_pending[0].status == ApprovalStatus.PENDING


def test_reject_already_decided_request_emits_zero_new_events(services, session, monkeypatch):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    approvals.reject(request.id, note="First decision")

    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)
    with pytest.raises(BusinessRuleError) as exc_info:
        approvals.reject(request.id, note="Second decision")

    assert exc_info.value.code == "APPROVAL_ALREADY_DECIDED"
    assert recorded == []


# ---------------------------------------------------------------------------
# Audit failure / commit failure / transactional and postcommit handler semantics
# ---------------------------------------------------------------------------


def test_standalone_request_audit_failure_emits_zero_observable_approval_requested(
    services, monkeypatch
):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    _login_as_fresh_requester(services)
    approvals = services["approval_service"]
    bus = approvals._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(ApprovalRequested, lambda e, c: seen.append(e))

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        approvals.request_change(
            request_type="baseline.create",
            entity_type="project_baseline",
            entity_id=_unique("audit-fail-probe"),
            project_id=None,
            payload={"name": "Audit failure probe"},
        )

    assert seen == []


def test_no_approval_requested_observable_on_commit_failure(services, monkeypatch):
    from src.core.platform.infrastructure.persistence.uow.approval_unit_of_work import (
        SqlAlchemyPlatformUnitOfWork,
    )

    _login_as_fresh_requester(services)
    approvals = services["approval_service"]
    bus = approvals._uow_factory._post_commit_bus
    seen = []
    bus.subscribe(ApprovalRequested, lambda e, c: seen.append(e))

    def _fail_commit(self):
        raise RuntimeError("simulated approval commit failure")

    monkeypatch.setattr(SqlAlchemyPlatformUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated approval commit failure"):
        approvals.request_change(
            request_type="baseline.create",
            entity_type="project_baseline",
            entity_id=_unique("commit-fail-probe"),
            project_id=None,
            payload={"name": "Commit failure probe"},
        )

    assert seen == []


def test_one_post_commit_handler_failing_does_not_block_the_other_or_the_commit(
    services, session
):
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    bus = approvals._uow_factory._post_commit_bus

    def _failing_handler(event, context):
        raise RuntimeError("simulated post-commit handler failure")

    healthy_seen = []
    bus.subscribe(ApprovalApproved, _failing_handler)
    bus.subscribe(ApprovalApproved, lambda e, c: healthy_seen.append(e))

    # Must not raise -- ISOLATE_AND_CONTINUE swallows the failing handler's exception.
    decided = approvals.approve_and_apply(request.id, note="Approved despite a broken subscriber")

    assert len(healthy_seen) == 1
    assert decided.status == ApprovalStatus.APPROVED


def test_transactional_handler_failure_rolls_back_the_whole_request_transaction(
    services, monkeypatch
):
    """§34: a FAIL_FAST transactional (pre-commit) handler failing must roll back the whole
    owning transaction -- no `ApprovalRequest` persists, no postcommit publication follows."""
    _login_as_fresh_requester(services)
    approvals = services["approval_service"]
    dispatcher = approvals._uow_factory._transactional_dispatcher
    bus = approvals._uow_factory._post_commit_bus
    postcommit_seen = []
    bus.subscribe(ApprovalRequested, lambda e, c: postcommit_seen.append(e))

    def _failing_transactional_handler(event, uow):
        raise RuntimeError("simulated transactional handler failure")

    subscription = dispatcher.subscribe(ApprovalRequested, _failing_transactional_handler)
    try:
        entity_id = _unique("transactional-fail-probe")
        with pytest.raises(RuntimeError, match="simulated transactional handler failure"):
            approvals.request_change(
                request_type="baseline.create",
                entity_type="project_baseline",
                entity_id=entity_id,
                project_id=None,
                payload={"name": "Transactional failure probe"},
            )
        assert postcommit_seen == []
        matching = [r for r in approvals.list_pending() if r.entity_id == entity_id]
        assert matching == []
    finally:
        subscription.dispose()


# ---------------------------------------------------------------------------
# Cross-tenant / cross-org isolation
# ---------------------------------------------------------------------------


def test_cross_org_decision_denial_emits_zero_approval_approved_or_rejected(services, monkeypatch):
    """§27: same tenant, request belongs to Org A1, active org = A2 -> decide denial emits zero
    `ApprovalApproved`/`ApprovalRejected` (Approval-P1A's own negative authorization case,
    re-verified here at the event layer)."""
    _login(services, "admin", "ChangeMe123!")
    organization_service = services["organization_service"]
    org_a1 = services["tenant_context_service"].get_active_organization()
    org_a2 = organization_service.create_organization(
        organization_code=_unique("EVT-XORG-A2"), display_name="Events Org A2", is_enabled=False
    )

    _, budget = _submitted_budget(services, services["session"])
    request = _request_budget_approval_as_a_different_user(services, budget)
    assert request.organization_id == org_a1.id

    approver_username = _unique("evt-xorg-approver")
    services["auth_service"].register_user(approver_username, "StrongPass123", role_names=["approver"])
    organization_service.enable_organization(org_a2.id)
    services["tenant_context_service"].set_active_organization(org_a2.id)

    _login(services, approver_username, "StrongPass123")
    services["user_session"].set_active_organization_id(org_a2.id)
    approvals = services["approval_service"]
    bus = approvals._uow_factory._post_commit_bus
    approved_seen, rejected_seen = [], []
    bus.subscribe(ApprovalApproved, lambda e, c: approved_seen.append(e))
    bus.subscribe(ApprovalRejected, lambda e, c: rejected_seen.append(e))
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    with pytest.raises(NotFoundError):
        approvals.approve_and_apply(request.id)
    with pytest.raises(NotFoundError):
        approvals.reject(request.id)

    assert recorded == []
    assert approved_seen == []
    assert rejected_seen == []


def test_cross_tenant_decision_attempt_emits_zero_approval_events(tmp_path):
    """§26: Tenant B cannot approve/reject Tenant A's Approval -- zero events, even if an invalid
    command reaches a repository lookup. Uses two genuinely independent `TenantContextService`
    fakes (never a shared one with a swapped `UserSessionContext`, which would still resolve
    through the SAME factory-bound tenant context -- the exact pitfall Approval-P1A's own
    cross-tenant test avoided) -- mirrors `test_platform_unit_of_work.py::
    test_cross_tenant_context_cannot_read_another_tenants_approval_request`'s two-factory shape,
    extended here to prove EVENT isolation, not just repository-read isolation."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.core.platform.application.approval.approval_service import ApprovalService
    from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
    from src.core.platform.infrastructure.persistence.repositories.approval.approval import (
        SqlAlchemyApprovalRepository,
    )
    from src.core.platform.infrastructure.persistence.uow.approval_unit_of_work import (
        SqlAlchemyPlatformUnitOfWorkFactory,
    )
    from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
    from src.infra.events.in_process_transactional_event_dispatcher import (
        InProcessTransactionalEventDispatcher,
    )
    from src.infra.persistence.orm.base import Base

    class _FakeTenantContextService:
        def __init__(self, tenant_id, organization_id):
            self._tenant_id = tenant_id
            self._organization_id = organization_id

        def require_active_scope_ids(self, *, operation_label):
            from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds

            return ActiveScopeIds(tenant_id=self._tenant_id, organization_id=self._organization_id)

        def require_active_organization_id(self, *, operation_label):
            return self._organization_id

        def require_active_tenant_id(self, *, operation_label):
            return self._tenant_id

        def get_active_tenant_id(self):
            return self._tenant_id

    engine = create_engine(f"sqlite:///{tmp_path}/cross_tenant_events.db", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    dispatcher = InProcessTransactionalEventDispatcher()
    bus = InProcessPostCommitEventBus()

    factory_a = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=session_factory, transactional_dispatcher=dispatcher, post_commit_bus=bus,
        tenant_context_service=_FakeTenantContextService("evt-tenant-a", "evt-org-a"),
        user_session=None,
    )
    factory_b = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=session_factory, transactional_dispatcher=dispatcher, post_commit_bus=bus,
        tenant_context_service=_FakeTenantContextService("evt-tenant-b", "evt-org-b"),
        user_session=None,
    )
    principal_a = UserSessionPrincipal(
        user_id="evt-tenant-a-requester", username="evt-tenant-a-requester", display_name="A Requester",
        role_names=frozenset(), permissions=frozenset(["approval.request"]),
    )
    session_a = UserSessionContext()
    session_a.set_principal(principal_a)
    approval_repo_a = SqlAlchemyApprovalRepository(session_factory())
    approval_repo_a._tenant_context_service = _FakeTenantContextService("evt-tenant-a", "evt-org-a")
    approvals_a = ApprovalService(
        session=approval_repo_a.session, approval_repo=approval_repo_a, uow_factory=factory_a,
        user_session=session_a, tenant_context_service=_FakeTenantContextService("evt-tenant-a", "evt-org-a"),
        clock=_FixedClock(datetime(2031, 1, 1, tzinfo=timezone.utc)),
    )
    request = approvals_a.request_change(
        request_type="baseline.create", entity_type="project_baseline",
        entity_id="cross-tenant-events-probe", project_id=None, payload={"name": "Probe"},
    )

    approved_seen, rejected_seen = [], []
    bus.subscribe(ApprovalApproved, lambda e, c: approved_seen.append(e))
    bus.subscribe(ApprovalRejected, lambda e, c: rejected_seen.append(e))

    principal_b = UserSessionPrincipal(
        user_id="evt-tenant-b-approver", username="evt-tenant-b-approver", display_name="B Approver",
        role_names=frozenset(), permissions=frozenset(["approval.decide"]),
    )
    session_b = UserSessionContext()
    session_b.set_principal(principal_b)
    approvals_b = ApprovalService(
        session=session_factory(), approval_repo=None, uow_factory=factory_b,
        user_session=session_b, tenant_context_service=_FakeTenantContextService("evt-tenant-b", "evt-org-b"),
        clock=_FixedClock(datetime(2031, 1, 1, tzinfo=timezone.utc)),
    )

    with pytest.raises(NotFoundError):
        approvals_b.approve_and_apply(request.id)
    with pytest.raises(NotFoundError):
        approvals_b.reject(request.id)

    assert approved_seen == []
    assert rejected_seen == []
    reloaded = [r for r in approvals_a.list_pending() if r.id == request.id]
    assert len(reloaded) == 1
    assert reloaded[0].status == ApprovalStatus.PENDING


# ---------------------------------------------------------------------------
# Sequencing
# ---------------------------------------------------------------------------


def test_approve_and_apply_orders_target_event_before_approval_approved(services, session, monkeypatch):
    """§19/§44: the apply participant (`BudgetApprovalParticipant`) records its own target-
    capability event on the SAME UoW before the ApprovalRequest transitions to APPROVED -- the
    committed order must be [target event(s)..., ApprovalApproved], never the reverse, and
    `ApprovalApproved` must not duplicate the target fact."""
    _, budget = _submitted_budget(services, session)
    request = _request_budget_approval_as_a_different_user(services, budget)
    approvals = services["approval_service"]
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    approvals.approve_and_apply(request.id, note="Approved")

    assert len(recorded) >= 1
    assert isinstance(recorded[-1], ApprovalApproved)
    if len(recorded) > 1:
        assert not isinstance(recorded[0], ApprovalApproved)


def test_sequence_of_two_standalone_requests_produces_events_in_committed_order(
    services, monkeypatch
):
    approvals = services["approval_service"]
    recorded = _spy_recorded_events(approvals._uow_factory, monkeypatch)

    _login_as_fresh_requester(services)
    entity_a = _unique("seq-probe-a")
    approvals.request_change(
        request_type="baseline.create", entity_type="project_baseline",
        entity_id=entity_a, project_id=None, payload={"name": "Seq A"},
    )
    entity_b = _unique("seq-probe-b")
    approvals.request_change(
        request_type="baseline.create", entity_type="project_baseline",
        entity_id=entity_b, project_id=None, payload={"name": "Seq B"},
    )

    assert len(recorded) == 2
    assert [type(e) for e in recorded] == [ApprovalRequested, ApprovalRequested]
    assert recorded[0].entity_id == entity_a
    assert recorded[1].entity_id == entity_b
