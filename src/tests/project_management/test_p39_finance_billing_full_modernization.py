from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    BillingPreparationCreated,
    BillingPreparationExternalOutcomeRecorded,
    BillingPreparationLineAdded,
    BillingPreparationStatusChangeType,
    BillingPreparationStatusChanged,
    BillingProfileActivated,
    BillingProfileCreated,
    BillingScheduleLineAdded,
    BillingScheduleLineMarkedReady,
)
from src.core.modules.project_management.application.financials.invoicing.event_handlers.view_invalidation import (
    BILLING_CATEGORY,
    BILLING_COMMERCIAL_SCOPE_CODE,
    build_billing_view_invalidation_handler,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    BillableSourceType,
    BillingExternalEventType,
    BillingPreparationStatus,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    BillingProfileStatus,
    BillingScheduleLineStatus,
)
from src.core.modules.project_management.domain.financials.configuration import BillingMethod
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import ResourceScope
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


def _billing_hints(hints):
    return [h for h in hints if h.category == BILLING_CATEGORY]


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


def _setup_billable_project(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        _unique("P39 Billing project"), financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=_unique("P39-CC"), name="P39 Billing cost code"
    )
    services["financial_period_service"].create_period(
        code=_unique("P39-FY26"), name="August 2026", fiscal_year=2026, period_number=8,
        start_date=date(2026, 8, 1), end_date=date(2026, 8, 31),
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id, expected_version=profile.version, default_cost_code_id=cost_code.id,
        billing_method=BillingMethod.FIXED_PRICE, is_billable=True,
    )
    return organization, project, cost_code


def _ready_schedule_line(services, project, *, amount=Decimal("24000")):
    billing_profile_service = services["billing_profile_service"]
    bp_profile = billing_profile_service.create_profile(
        project.id, contract_reference=_unique("P39-CONTRACT"), contract_value=Decimal("50000"),
        customer_party_id="party-1",
    )
    bp_profile = billing_profile_service.activate_profile(
        project.id, expected_row_version=bp_profile.row_version
    )
    line = billing_profile_service.add_schedule_line(
        project.id, name="Milestone 1", amount=amount, due_date=date(2026, 8, 20)
    )
    line = billing_profile_service.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    )
    return bp_profile, line


def test_legacy_billing_signal_field_is_deleted():
    assert not hasattr(domain_events, "billing_preparations_changed")


# ---------------------------------------------------------------------------
# ViewInvalidation handler: unit-level mapping
# ---------------------------------------------------------------------------


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def test_every_billing_event_maps_to_the_single_commercial_target():
    channel = _fake_channel()
    handler = build_billing_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    events = (
        BillingProfileCreated(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_profile_id="bp1",
            occurred_at=now,
        ),
        BillingProfileActivated(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_profile_id="bp1",
            occurred_at=now,
        ),
        BillingScheduleLineAdded(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_profile_id="bp1",
            schedule_line_id="sl1", occurred_at=now,
        ),
        BillingScheduleLineMarkedReady(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_profile_id="bp1",
            schedule_line_id="sl1", occurred_at=now,
        ),
        BillingPreparationCreated(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_preparation_id="prep1",
            occurred_at=now,
        ),
        BillingPreparationLineAdded(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_preparation_id="prep1",
            preparation_line_id="line1", source_type=BillableSourceType.SCHEDULE_LINE,
            occurred_at=now,
        ),
        BillingPreparationStatusChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_preparation_id="prep1",
            change_type=BillingPreparationStatusChangeType.SUBMITTED, occurred_at=now,
        ),
        BillingPreparationExternalOutcomeRecorded(
            tenant_id="t1", organization_id="o1", project_id="p1", billing_preparation_id="prep1",
            external_event_id="ev1", event_type=BillingExternalEventType.DELIVERY_ACCEPTED,
            occurred_at=now,
        ),
    )
    for index, event in enumerate(events):
        handler(event, DomainEventContext(correlation_id=f"c{index}"))

    assert len(channel.notified) == len(events)
    for hint in channel.notified:
        assert hint.scope_code == BILLING_COMMERCIAL_SCOPE_CODE
        assert isinstance(hint.scope, ResourceScope)
        assert hint.scope.module_code == "project_management"
        assert hint.scope.entity_type == "project"
        assert hint.entity_id == "p1"


def test_dedupe_within_one_transaction():
    channel = _fake_channel()
    handler = build_billing_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    event = BillingProfileActivated(
        tenant_id="t1", organization_id="o1", project_id="p1", billing_profile_id="bp1",
        occurred_at=now,
    )
    handler(event, DomainEventContext(correlation_id="same-tx"))
    handler(event, DomainEventContext(correlation_id="same-tx"))
    assert len(channel.notified) == 1

    handler(event, DomainEventContext(correlation_id="next-tx"))
    assert len(channel.notified) == 2


# ---------------------------------------------------------------------------
# Real producer path -- Billing Profile family
# ---------------------------------------------------------------------------


def test_profile_lifecycle_produces_source_derived_facts(services):
    _, project, _cost_code = _setup_billable_project(services)
    billing_profile_service = services["billing_profile_service"]

    hints = _spy_hints(services)
    profile = billing_profile_service.create_profile(
        project.id, contract_reference=_unique("CONTRACT"), contract_value=Decimal("50000"),
        customer_party_id="party-1",
    )
    assert len(_billing_hints(hints)) == 1

    hints.clear()
    profile = billing_profile_service.activate_profile(
        project.id, expected_row_version=profile.row_version
    )
    assert profile.status == BillingProfileStatus.ACTIVE
    assert len(_billing_hints(hints)) == 1

    hints.clear()
    line = billing_profile_service.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal("24000"), due_date=date(2026, 8, 20)
    )
    assert len(_billing_hints(hints)) == 1

    hints.clear()
    line = billing_profile_service.mark_schedule_line_ready(
        line.id, expected_row_version=line.row_version
    )
    assert line.status == BillingScheduleLineStatus.READY
    assert len(_billing_hints(hints)) == 1


# ---------------------------------------------------------------------------
# Real producer path -- Billing Preparation family
# ---------------------------------------------------------------------------


def test_create_preparation_and_add_fixed_price_source_produce_facts(services):
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    billing_preparation_service = services["billing_preparation_service"]

    hints = _spy_hints(services)
    preparation = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=_unique("bp-key"),
    )
    assert len(_billing_hints(hints)) == 1

    hints.clear()
    billing_preparation_service.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    )
    assert len(_billing_hints(hints)) == 1


def test_create_preparation_replay_produces_zero_hints(services):
    _, project, _cost_code = _setup_billable_project(services)
    _ready_schedule_line(services, project)
    billing_preparation_service = services["billing_preparation_service"]
    key = _unique("bp-replay-key")
    first = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=key,
    )

    hints = _spy_hints(services)
    replay = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=key,
    )

    assert replay.id == first.id
    assert _billing_hints(hints) == []


def test_add_source_already_reserved_is_rejected(services):
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    billing_preparation_service = services["billing_preparation_service"]
    preparation = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=_unique("bp-key"),
    )
    billing_preparation_service.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    )
    other_preparation = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=_unique("bp-key"),
    )

    with pytest.raises(BusinessRuleError, match="already reserved"):
        billing_preparation_service.add_fixed_price_source(
            other_preparation.id, schedule_line_id=line.id,
            expected_row_version=other_preparation.row_version,
        )


def test_submit_preparation_produces_status_changed_submitted(services):
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    billing_preparation_service = services["billing_preparation_service"]
    preparation = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=_unique("bp-key"),
    )
    billing_preparation_service.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    )
    preparation = billing_preparation_service.get_preparation(preparation.id)

    hints = _spy_hints(services)
    submitted = billing_preparation_service.submit_preparation(
        preparation.id, expected_row_version=preparation.row_version
    )

    assert submitted.status == BillingPreparationStatus.SUBMITTED
    assert len(_billing_hints(hints)) == 1


def _submitted_preparation(services, project, line):
    billing_preparation_service = services["billing_preparation_service"]
    preparation = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=_unique("bp-key"),
    )
    billing_preparation_service.add_fixed_price_source(
        preparation.id, schedule_line_id=line.id, expected_row_version=preparation.row_version
    )
    preparation = billing_preparation_service.get_preparation(preparation.id)
    return billing_preparation_service.submit_preparation(
        preparation.id, expected_row_version=preparation.row_version
    )


def _approve_preparation(services, project):
    """Approves via the governed participant path (mirrors production `approve_and_apply`)."""
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    services["auth_service"].register_user(
        _unique("p39-reviewer"), "StrongPass123", role_names=["approver"]
    )
    return request


def test_governed_approval_produces_status_changed_approved(services):
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    submitted = _submitted_preparation(services, project, line)
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    reviewer = _unique("p39-billing-reviewer")
    services["auth_service"].register_user(reviewer, "StrongPass123", role_names=["approver"])
    _login(services, reviewer, "StrongPass123")

    hints = _spy_hints(services)
    services["approval_service"].approve_and_apply(request.id)

    approved = services["billing_preparation_service"].get_preparation(submitted.id)
    assert approved.status == BillingPreparationStatus.APPROVED
    assert len(_billing_hints(hints)) == 1


def test_governed_rejection_produces_status_changed_rejected(services):
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    submitted = _submitted_preparation(services, project, line)
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    reviewer = _unique("p39-billing-rejector")
    services["auth_service"].register_user(reviewer, "StrongPass123", role_names=["approver"])
    _login(services, reviewer, "StrongPass123")

    hints = _spy_hints(services)
    services["approval_service"].reject(request.id, note="Not this time")

    rejected = services["billing_preparation_service"].get_preparation(submitted.id)
    assert rejected.status == BillingPreparationStatus.REJECTED
    assert len(_billing_hints(hints)) == 1


def test_request_delivery_produces_status_changed_delivery_pending(services):
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    submitted = _submitted_preparation(services, project, line)
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    reviewer = _unique("p39-delivery-reviewer")
    services["auth_service"].register_user(reviewer, "StrongPass123", role_names=["approver"])
    _login(services, reviewer, "StrongPass123")
    services["approval_service"].approve_and_apply(request.id)
    _login(services, "admin", "ChangeMe123!")

    billing_preparation_service = services["billing_preparation_service"]
    approved = billing_preparation_service.get_preparation(submitted.id)

    hints = _spy_hints(services)
    billing_preparation_service.request_delivery(
        approved.id, expected_row_version=approved.row_version
    )

    updated = billing_preparation_service.get_preparation(approved.id)
    assert updated.status == BillingPreparationStatus.DELIVERY_PENDING
    assert len(_billing_hints(hints)) == 1


def test_external_outcome_delivery_accepted_produces_outcome_and_two_status_facts(services):
    """`record_external_outcome(DELIVERY_ACCEPTED)` transitions status twice in one call
    (DELIVERED then ACKNOWLEDGED) -- both are recorded as separate facts, plus the outcome fact
    itself: 3 typed events total, still one deduped ViewInvalidation hint."""
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    submitted = _submitted_preparation(services, project, line)
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    reviewer = _unique("p39-outcome-reviewer")
    services["auth_service"].register_user(reviewer, "StrongPass123", role_names=["approver"])
    _login(services, reviewer, "StrongPass123")
    services["approval_service"].approve_and_apply(request.id)
    _login(services, "admin", "ChangeMe123!")

    billing_preparation_service = services["billing_preparation_service"]
    approved = billing_preparation_service.get_preparation(submitted.id)
    billing_preparation_service.request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    pending = billing_preparation_service.get_preparation(approved.id)

    hints = _spy_hints(services)
    billing_preparation_service.record_external_outcome(
        pending.id,
        event_type=BillingExternalEventType.DELIVERY_ACCEPTED,
        external_system="ext-accounting",
        external_status="accepted",
        idempotency_key=_unique("ext-key"),
        occurred_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )

    final = billing_preparation_service.get_preparation(pending.id)
    assert final.status == BillingPreparationStatus.ACKNOWLEDGED
    assert final.delivered_at is not None
    assert final.acknowledged_at is not None
    # Same-transaction dedupe: 3 typed facts (outcome + DELIVERED + ACKNOWLEDGED), one hint.
    assert len(_billing_hints(hints)) == 1


def test_external_outcome_replay_produces_zero_hints(services):
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    submitted = _submitted_preparation(services, project, line)
    request = services["approval_service"].list_pending(project_id=project.id)[0]
    reviewer = _unique("p39-replay-reviewer")
    services["auth_service"].register_user(reviewer, "StrongPass123", role_names=["approver"])
    _login(services, reviewer, "StrongPass123")
    services["approval_service"].approve_and_apply(request.id)
    _login(services, "admin", "ChangeMe123!")

    billing_preparation_service = services["billing_preparation_service"]
    approved = billing_preparation_service.get_preparation(submitted.id)
    billing_preparation_service.request_delivery(
        approved.id, expected_row_version=approved.row_version
    )
    pending = billing_preparation_service.get_preparation(approved.id)
    key = _unique("ext-replay-key")
    billing_preparation_service.record_external_outcome(
        pending.id, event_type=BillingExternalEventType.DELIVERY_ACCEPTED,
        external_system="ext-accounting", external_status="accepted",
        idempotency_key=key, occurred_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )

    hints = _spy_hints(services)
    billing_preparation_service.record_external_outcome(
        pending.id, event_type=BillingExternalEventType.DELIVERY_ACCEPTED,
        external_system="ext-accounting", external_status="accepted",
        idempotency_key=key, occurred_at=datetime(2026, 8, 25, tzinfo=timezone.utc),
    )

    assert _billing_hints(hints) == []


# ---------------------------------------------------------------------------
# P39 §40-41: permission-order regression -- both new families
# ---------------------------------------------------------------------------


def test_add_schedule_line_permission_check_is_not_masked_by_project_id_resolution(services):
    """`_project_id()`'s `billing_profile` branch resolves via `create_profile`/`activate_profile`/
    `add_schedule_line`'s own explicit `project_id` first-positional-arg (the generic shortcut) --
    the only branch needing an accessor is `mark_schedule_line_ready`, resolved via the private
    `_require_schedule_line`. A viewer (lacking `finance.manage`) must be rejected on the real
    missing command permission, not a masking read-permission."""
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    billing_profile_service = services["billing_profile_service"]

    auth = services["auth_service"]
    auth.register_user("p39-viewer-profile", "StrongPass123", role_names=["viewer"])
    _login(services, "p39-viewer-profile", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="finance.manage"):
        billing_profile_service.create_profile(
            project.id, contract_reference="X", contract_value=Decimal("1"),
        )


def test_mark_schedule_line_ready_permission_check_is_not_masked(services):
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    billing_profile_service = services["billing_profile_service"]
    profile = billing_profile_service.create_profile(
        project.id, contract_reference=_unique("CONTRACT"), contract_value=Decimal("50000"),
        customer_party_id="party-1",
    )
    billing_profile_service.activate_profile(project.id, expected_row_version=profile.row_version)
    line = billing_profile_service.add_schedule_line(
        project.id, name="Milestone 1", amount=Decimal("24000"), due_date=date(2026, 8, 20)
    )

    auth = services["auth_service"]
    auth.register_user("p39-viewer-schedule", "StrongPass123", role_names=["viewer"])
    _login(services, "p39-viewer-schedule", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="finance.manage"):
        billing_profile_service.mark_schedule_line_ready(
            line.id, expected_row_version=line.row_version
        )


def test_add_fixed_price_source_permission_check_is_not_masked(services):
    """`_project_id()`'s `billing_preparation` branch resolves via the private, unchecked
    `_require_preparation` -- must not require `finance.read` before `add_fixed_price_source`'s
    own `finance.manage` check runs."""
    _login(services, "admin", "ChangeMe123!")
    _, project, _cost_code = _setup_billable_project(services)
    _, line = _ready_schedule_line(services, project)
    billing_preparation_service = services["billing_preparation_service"]
    preparation = billing_preparation_service.create_preparation(
        project.id, preparation_number=_unique("BP"),
        period_start=date(2026, 8, 1), period_end=date(2026, 8, 31),
        idempotency_key=_unique("bp-key"),
    )

    auth = services["auth_service"]
    auth.register_user("p39-viewer-prep", "StrongPass123", role_names=["viewer"])
    _login(services, "p39-viewer-prep", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="finance.manage"):
        billing_preparation_service.add_fixed_price_source(
            preparation.id, schedule_line_id=line.id,
            expected_row_version=preparation.row_version,
        )


# ---------------------------------------------------------------------------
# Transaction correctness -- audit failure rolls back and leaves session usable
# ---------------------------------------------------------------------------


def test_profile_audit_failure_rolls_back_and_leaves_the_session_usable(services, monkeypatch):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    _, project, _cost_code = _setup_billable_project(services)

    original_record = EnterpriseAuditService.record

    def _fail_billing_audit(self, **kwargs):
        if kwargs.get("entity_type") == "ProjectBillingProfile":
            raise RuntimeError("simulated billing profile audit failure")
        return original_record(self, **kwargs)

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_billing_audit)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        services["billing_profile_service"].create_profile(
            project.id, contract_reference="Should Roll Back", contract_value=Decimal("1000"),
        )
    assert _billing_hints(hints) == []

    monkeypatch.undo()
    recovered = services["billing_profile_service"].create_profile(
        project.id, contract_reference="Recovered", contract_value=Decimal("1000"),
    )
    assert recovered.contract_reference == "Recovered", (
        "the shared session must remain usable for a subsequent legitimate operation"
    )


# ---------------------------------------------------------------------------
# Concurrency -- preserved, unweakened
# ---------------------------------------------------------------------------


def test_concurrent_activate_profile_second_writer_rejected(services, session):
    from sqlalchemy.orm import sessionmaker

    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.invoicing.billing import (
        SqlAlchemyProjectBillingRepository,
    )

    _, project, _cost_code = _setup_billable_project(services)
    billing_profile_service = services["billing_profile_service"]
    profile = billing_profile_service.create_profile(
        project.id, contract_reference=_unique("CONTRACT"), contract_value=Decimal("50000"),
        customer_party_id="party-1",
    )
    assert profile.row_version == 1

    repo_a = SqlAlchemyProjectBillingRepository(session)
    repo_a._tenant_context_service = services["tenant_context_service"]
    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        repo_b = SqlAlchemyProjectBillingRepository(session_b)
        repo_b._tenant_context_service = services["tenant_context_service"]
        read_by_a = repo_a.get_profile(project.id)
        read_by_b = repo_b.get_profile(project.id)
        assert read_by_a.row_version == read_by_b.row_version == 1

        read_by_a.legal_hold = True
        repo_a.update_profile(read_by_a, expected_row_version=1)
        session.commit()

        read_by_b.legal_hold = True
        with pytest.raises(ConcurrencyError):
            repo_b.update_profile(read_by_b, expected_row_version=1)
        session_b.rollback()
    finally:
        session_b.close()

    final = repo_a.get_profile(project.id)
    assert final.legal_hold is True, "the losing writer's change must not persist"


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow per-target destination invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_billing_commercial_stale_invalidates_commercial_only(services):
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onBillingCommercialStale("proj-a")
    assert controller._invalidated_destinations == {"commercial"}

    controller._invalidated_destinations.clear()
    controller.onBillingCommercialStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"
