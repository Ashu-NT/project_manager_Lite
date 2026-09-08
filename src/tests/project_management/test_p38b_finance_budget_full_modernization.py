from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetLineChangeType,
    BudgetLineChanged,
    BudgetProfileUpdated,
    BudgetRemoved,
    BudgetStatusChangeType,
    BudgetStatusChanged,
    BudgetVersionCreated,
)
from src.core.modules.project_management.application.financials.budgets.event_handlers.view_invalidation import (
    BUDGET_CATEGORY,
    BUDGET_PLANNING_SCOPE_CODE,
    BUDGET_PROJECT_SUMMARY_SCOPE_CODE,
    build_budget_view_invalidation_handler,
)
from src.core.modules.project_management.domain.financials.budget import BudgetStatus
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import ResourceScope
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog


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


def _budget_hints(hints):
    return [h for h in hints if h.category == BUDGET_CATEGORY]


def _login(services, username: str, password: str) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    user_session.set_principal(auth.build_principal(user))


_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _setup(services):
    project = services["project_service"].create_project(
        _unique("P38B Budget project"), financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code=_unique("P38B-CC"), name="P38B Cost Code"
    )
    return project, cost_code


def test_legacy_budget_signal_field_is_deleted():
    assert not hasattr(domain_events, "budgets_changed")


# ---------------------------------------------------------------------------
# ViewInvalidation handler: unit-level mapping/dedupe
# ---------------------------------------------------------------------------


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def test_every_budget_event_maps_to_both_planning_and_summary_targets():
    """Source-preserving design: the legacy `budgets_changed` signal never differentiated by fact
    type either -- both of its consumers reacted to every emission uniformly."""
    channel = _fake_channel()
    handler = build_budget_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    events = (
        BudgetVersionCreated(
            tenant_id="t1", organization_id="o1", project_id="p1", budget_id="b1",
            status=BudgetStatus.DRAFT, predecessor_budget_id=None, occurred_at=now,
        ),
        BudgetProfileUpdated(
            tenant_id="t1", organization_id="o1", project_id="p1", budget_id="b1", occurred_at=now,
        ),
        BudgetLineChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", budget_id="b1",
            budget_line_id="l1", change_type=BudgetLineChangeType.ADDED, occurred_at=now,
        ),
        BudgetStatusChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", budget_id="b1",
            change_type=BudgetStatusChangeType.SUBMITTED, occurred_at=now,
        ),
        BudgetRemoved(
            tenant_id="t1", organization_id="o1", project_id="p1", budget_id="b1", occurred_at=now,
        ),
    )
    for index, event in enumerate(events):
        handler(event, DomainEventContext(correlation_id=f"c{index}"))

    assert len(channel.notified) == len(events) * 2
    for hint in channel.notified:
        assert isinstance(hint.scope, ResourceScope)
        assert hint.scope.module_code == "project_management"
        assert hint.scope.entity_type == "project"
        assert hint.entity_id == "p1"
    scope_codes = {hint.scope_code for hint in channel.notified}
    assert scope_codes == {BUDGET_PLANNING_SCOPE_CODE, BUDGET_PROJECT_SUMMARY_SCOPE_CODE}


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_budget_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    event = BudgetProfileUpdated(
        tenant_id="t1", organization_id="o1", project_id="p1", budget_id="b1", occurred_at=now
    )
    handler(event, DomainEventContext(correlation_id="same-tx"))
    handler(event, DomainEventContext(correlation_id="same-tx"))
    assert len(channel.notified) == 2, "same two targets within one transaction coalesce"

    handler(event, DomainEventContext(correlation_id="next-tx"))
    assert len(channel.notified) == 4, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real producer path -- direct commands, canonical FinanceGovernanceUnitOfWork
# ---------------------------------------------------------------------------


def test_create_budget_produces_version_created_hints(services):
    project, _cost_code = _setup(services)
    hints = _spy_hints(services)

    budget = services["budget_service"].create_budget(project.id, "P38B Budget")

    budget_hints = _budget_hints(hints)
    assert {h.scope_code for h in budget_hints} == {
        BUDGET_PLANNING_SCOPE_CODE, BUDGET_PROJECT_SUMMARY_SCOPE_CODE
    }
    assert all(h.entity_id == project.id for h in budget_hints)
    assert budget.status == BudgetStatus.DRAFT


def test_add_update_delete_line_each_produce_hints(services):
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "P38B Budget")

    hints = _spy_hints(services)
    line = budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=budget.row_version,
    )
    assert len(_budget_hints(hints)) == 2

    hints.clear()
    budget = budgets.get_budget(budget.id)
    budgets.update_line(
        line.id, expected_line_version=line.row_version, expected_budget_version=budget.row_version,
        amount=Decimal("150"),
    )
    assert len(_budget_hints(hints)) == 2

    hints.clear()
    budget = budgets.get_budget(budget.id)
    line = budgets.list_lines(budget.id)[0]
    budgets.delete_line(
        line.id, expected_line_version=line.row_version, expected_budget_version=budget.row_version,
    )
    assert len(_budget_hints(hints)) == 2


def test_update_header_produces_profile_updated_fact(services):
    project, _cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "P38B Budget")

    hints = _spy_hints(services)
    budgets.update_budget_header(budget.id, name="Renamed Budget", expected_version=budget.row_version)

    budget_hints = _budget_hints(hints)
    assert len(budget_hints) == 2


def test_delete_budget_produces_removed_fact(services):
    project, _cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "P38B Budget")

    hints = _spy_hints(services)
    budgets.delete_budget(budget.id, expected_version=budget.row_version)

    assert len(_budget_hints(hints)) == 2
    assert budgets.list_budgets_for_project(project.id) == []


def test_submit_and_direct_approve_progression_produces_status_changed_facts(services):
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "P38B Budget")
    budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)

    hints = _spy_hints(services)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    assert len(_budget_hints(hints)) == 2

    hints.clear()
    result = budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)
    approved_hints = _budget_hints(hints)
    assert result.outcome.value == "applied"
    # No prior approved budget for this project -- only the APPROVED fact, no SUPERSEDED one.
    assert len(approved_hints) == 2


def test_reject_produces_status_changed_fact(services):
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "P38B Budget")
    budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)

    hints = _spy_hints(services)
    rejected = budgets.reject_budget(budget.id, rejected_by="admin", expected_version=budget.row_version)

    assert rejected.status == BudgetStatus.REJECTED
    assert len(_budget_hints(hints)) == 2


def test_close_produces_status_changed_fact(services):
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "P38B Budget")
    budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    result = budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)
    approved = budgets.get_budget(result.budget_id)

    hints = _spy_hints(services)
    closed = budgets.close_budget(approved.id, "admin", expected_version=approved.row_version)

    assert closed.status == BudgetStatus.CLOSED
    assert len(_budget_hints(hints)) == 2


def test_approving_a_successor_supersedes_the_previous_approved_version(services):
    """A single approval decision that supersedes a prior approved budget legitimately produces
    TWO `BudgetStatusChanged` facts -- one per affected `ProjectBudget` row."""
    project, cost_code = _setup(services)
    budgets = services["budget_service"]

    first = budgets.create_budget(project.id, "V1")
    budgets.add_line(
        first.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=first.row_version,
    )
    first = budgets.get_budget(first.id)
    first = budgets.submit_budget(first.id, "admin", expected_version=first.row_version)
    result = budgets.approve_budget(first.id, approved_by="admin", expected_version=first.row_version)
    approved_first = budgets.get_budget(result.budget_id)

    successor = budgets.create_successor(approved_first.id, name="V2")
    successor = budgets.submit_budget(successor.id, "admin", expected_version=successor.row_version)

    hints = _spy_hints(services)
    budgets.approve_budget(successor.id, approved_by="admin", expected_version=successor.row_version)

    approved_hints = _budget_hints(hints)
    # Both the successor and the now-superseded predecessor are project-scoped facts for the
    # same project -- planning + summary targets for each, still deduped by target within the
    # one transaction (2 targets total, not 4).
    assert len(approved_hints) == 2

    predecessor_after = budgets.get_budget(approved_first.id)
    assert predecessor_after.status == BudgetStatus.SUPERSEDED


def test_create_successor_alone_does_not_supersede_the_predecessor(services):
    """`create_successor` only creates a new DRAFT -- supersession is an approval-time fact, not a
    creation-time one (confirmed by direct source reading, not assumed)."""
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    first = budgets.create_budget(project.id, "V1")
    budgets.add_line(
        first.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=first.row_version,
    )
    first = budgets.get_budget(first.id)
    first = budgets.submit_budget(first.id, "admin", expected_version=first.row_version)
    result = budgets.approve_budget(first.id, approved_by="admin", expected_version=first.row_version)
    approved_first = budgets.get_budget(result.budget_id)

    hints = _spy_hints(services)
    budgets.create_successor(approved_first.id, name="V2")

    assert len(_budget_hints(hints)) == 2
    unchanged = budgets.get_budget(approved_first.id)
    assert unchanged.status == BudgetStatus.APPROVED


# ---------------------------------------------------------------------------
# Approval-participant path -- governed decisions, same typed facts
# ---------------------------------------------------------------------------


def test_governed_approval_participant_emits_the_same_typed_status_fact(services, monkeypatch):
    monkeypatch.setenv("PM_GOVERNANCE_MODE", "required")
    monkeypatch.setenv("PM_GOVERNANCE_ACTIONS", "budget.approve")
    _login(services, "admin", "ChangeMe123!")
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    approvals = services["approval_service"]

    budget = budgets.create_budget(project.id, "P38B Governed")
    budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)

    result = budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)
    assert result.outcome.value == "pending_approval"
    request_id = approvals.list_pending(project_id=project.id)[0].id

    services["auth_service"].register_user(
        "p38b-budget-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "p38b-budget-reviewer", "StrongPass123")

    hints = _spy_hints(services)
    approvals.approve_and_apply(request_id)

    approved_hints = _budget_hints(hints)
    assert len(approved_hints) == 2
    approved = budgets.get_budget(budget.id)
    assert approved.status == BudgetStatus.APPROVED


# ---------------------------------------------------------------------------
# Cross-capability path -- Financial Change applying through the Budget authority
# ---------------------------------------------------------------------------


def test_financial_change_application_produces_budget_and_financial_change_facts_together(services):
    """The most important cross-capability proof: one ApprovalService transaction produces BOTH a
    typed `FinancialChangeChanged` fact and typed Budget facts (`BudgetVersionCreated` for the new
    successor, `BudgetStatusChanged(SUPERSEDED)` for the base) in the same commit."""
    from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
        FinancialChangeChanged,
    )
    from src.core.modules.project_management.domain.financials.financial_change import (
        FinancialChangeImpactType,
    )

    _login(services, "admin", "ChangeMe123!")
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    changes = services["financial_change_service"]
    principal = services["user_session"].principal

    budget = budgets.create_budget(project.id, "FC Base Budget")
    line = budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Scope",
        amount=Decimal("100"), expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    result = budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)
    approved_budget = budgets.get_budget(result.budget_id)

    change = changes.create_change(
        project.id, title="Scope increase", reason="Customer request",
        effective_date=date(2026, 6, 1), created_by=principal.user_id,
    )
    changes.add_impact(
        change.id, impact_type=FinancialChangeImpactType.BUDGET, description="Increase scope",
        amount=Decimal("25"), cost_code_id=cost_code.id, target_line_id=line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    change = changes.submit_change(change.id, submitted_by=principal.user_id, expected_version=change.row_version)
    request_id = services["approval_service"].list_pending(project_id=project.id)[0].id

    services["auth_service"].register_user(
        "p38b-fc-reviewer", "StrongPass123", role_names=["approver"]
    )
    _login(services, "p38b-fc-reviewer", "StrongPass123")

    hints = _spy_hints(services)
    services["approval_service"].approve_and_apply(request_id)

    budget_hints = _budget_hints(hints)
    assert len(budget_hints) == 2

    superseded = budgets.get_budget(approved_budget.id)
    assert superseded.status == BudgetStatus.SUPERSEDED
    applied_change = changes.get_change(change.id)
    assert applied_change.applied_budget_id
    successor = budgets.get_budget(applied_change.applied_budget_id)
    assert successor.status == BudgetStatus.APPROVED
    assert successor.predecessor_budget_id == approved_budget.id


# ---------------------------------------------------------------------------
# P38B §21: latent permission-order bug -- fixed for the Budget branch
# ---------------------------------------------------------------------------


def test_add_line_permission_check_is_not_masked_by_project_id_resolution(services):
    """`_project_id()`'s Budget branch must resolve the target budget's project_id without
    requiring `finance.read` -- a viewer (who has neither `finance.read` nor `budget.manage`) must
    be rejected on the actual missing command permission (`budget.manage`), not on the read
    permission the boundary's own identity resolution used to require first (the exact P37-FIX
    regression pattern, fixed here for Budget)."""
    _login(services, "admin", "ChangeMe123!")
    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Permission Order Budget")

    auth = services["auth_service"]
    auth.register_user("p38b-viewer", "StrongPass123", role_names=["viewer"])
    _login(services, "p38b-viewer", "StrongPass123")

    with pytest.raises(BusinessRuleError, match="budget.manage"):
        budgets.add_line(
            budget.id, cost_code_id=cost_code.id, description="Line",
            amount=Decimal("100"), expected_budget_version=budget.row_version,
        )


# ---------------------------------------------------------------------------
# Transaction correctness -- audit failure rolls back and leaves session usable
# ---------------------------------------------------------------------------


def test_audit_failure_rolls_back_and_leaves_the_session_usable(services, monkeypatch):
    """The failed attempt's own project is deliberately not reused for the recovery call --
    `create_budget`'s pre-commit `session.begin_nested()` SAVEPOINT combined with
    `sqlite:///:memory:`'s `SingletonThreadPool` makes a real cross-session post-rollback read of
    THIS SPECIFIC nested-transaction shape unreliable in this exact test topology (the same
    documented pysqlite legacy-driver limitation already noted for `BudgetService._apply_approval_
    decision` in `test_approval_service_unit_of_work_cutover.py`), independent of whether the
    underlying rollback is correct. A fresh project for the recovery call still proves the shared
    session remains usable for a subsequent legitimate operation, without depending on that
    unreliable read."""
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    failed_project, _cost_code = _setup(services)

    original_record = EnterpriseAuditService.record

    def _fail_budget_audit(self, **kwargs):
        if kwargs.get("entity_type") == "project_budget":
            raise RuntimeError("simulated budget audit failure")
        return original_record(self, **kwargs)

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_budget_audit)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        services["budget_service"].create_budget(failed_project.id, "Should Roll Back")
    assert _budget_hints(hints) == []

    monkeypatch.undo()
    recovery_project, _cost_code2 = _setup(services)
    recovered = services["budget_service"].create_budget(recovery_project.id, "Recovered Budget")
    assert recovered.name == "Recovered Budget", (
        "the shared session must remain usable for a subsequent legitimate operation"
    )


# ---------------------------------------------------------------------------
# Concurrency -- preserved, unweakened
# ---------------------------------------------------------------------------


def test_concurrent_update_line_second_writer_rejected(services, session):
    from sqlalchemy.orm import sessionmaker

    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.budgets.budget import (
        SqlAlchemyProjectBudgetRepository,
    )

    project, cost_code = _setup(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Concurrency Budget")
    line = budgets.add_line(
        budget.id, cost_code_id=cost_code.id, description="Line",
        amount=Decimal("100"), expected_budget_version=budget.row_version,
    )
    assert line.row_version == 1

    repo_a = SqlAlchemyProjectBudgetRepository(session)
    repo_a._tenant_context_service = services["tenant_context_service"]
    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        repo_b = SqlAlchemyProjectBudgetRepository(session_b)
        repo_b._tenant_context_service = services["tenant_context_service"]
        read_by_a = repo_a.get_line(line.id)
        read_by_b = repo_b.get_line(line.id)
        assert read_by_a.row_version == read_by_b.row_version == 1

        read_by_a.description = "Writer A wins"
        repo_a.update_line(read_by_a, expected_row_version=1)
        session.commit()

        read_by_b.description = "Writer B loses"
        with pytest.raises(ConcurrencyError):
            repo_b.update_line(read_by_b, expected_row_version=1)
        session_b.rollback()
    finally:
        session_b.close()

    final = repo_a.get_line(line.id)
    assert final.description == "Writer A wins", "the losing writer's change must not persist"


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow per-target destination invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_budget_planning_stale_invalidates_the_legacy_three(services):
    """Preserves the legacy `budgets_changed` signal's own 3-destination fan-out
    (overview/planning/performance) exactly."""
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onBudgetPlanningStale("proj-a")
    assert controller._invalidated_destinations == {"overview", "planning", "performance"}

    controller._invalidated_destinations.clear()
    controller.onBudgetPlanningStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"
