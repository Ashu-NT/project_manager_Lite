from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryRecorded,
    CostEntryRemoved,
    CostEntryReversed,
    CostEntryStatusChangeType,
    CostEntryStatusChanged,
    CostEntryUpdated,
)
from src.core.modules.project_management.application.financials.cost.entries.event_handlers.view_invalidation import (
    COST_ENTRY_ACTUALS_SCOPE_CODE,
    COST_ENTRY_CATEGORY,
    COST_ENTRY_LIST_SCOPE_CODE,
    build_cost_entry_view_invalidation_handler,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryStatus,
)
from src.core.platform.common.exceptions import ConcurrencyError
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


def _cost_entry_hints(hints):
    return [h for h in hints if h.category == COST_ENTRY_CATEGORY]


def _setup(services):
    organization = services["tenant_context_service"].get_active_organization()
    project = services["project_service"].create_project(
        "P37 Cost Entry project", financial_currency_code=organization.base_currency
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="P37-LABOR", name="P37 Labor"
    )
    period = services["financial_period_service"].create_period(
        code="P37-2026-01", name="January 2026", fiscal_year=2026, period_number=1,
        start_date=date(2026, 1, 1), end_date=date(2026, 1, 31),
    )
    return organization, project, cost_code, period


def _create_draft(services, project, cost_code, *, command_id="p37-manual-1", amount="100.00"):
    organization = services["tenant_context_service"].get_active_organization()
    return services["cost_entry_service"].create_manual_entry(
        project_id=project.id,
        command_id=command_id,
        description="P37 manual entry",
        amount=Decimal(amount),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 12),
        cost_code_id=cost_code.id,
    )


def test_legacy_cost_entry_signal_field_is_deleted():
    assert not hasattr(domain_events, "cost_entries_changed")


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


def test_draft_recorded_maps_to_list_target_only():
    channel = _fake_channel()
    handler = build_cost_entry_view_invalidation_handler(channel)
    event = CostEntryRecorded(
        tenant_id="t1", organization_id="o1", project_id="p1", cost_entry_id="e1",
        status=ProjectCostEntryStatus.DRAFT, occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="c1"))
    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.scope_code == COST_ENTRY_LIST_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "project"
    assert hint.entity_id == "p1"


def test_posted_recorded_maps_to_both_list_and_actuals_targets():
    channel = _fake_channel()
    handler = build_cost_entry_view_invalidation_handler(channel)
    event = CostEntryRecorded(
        tenant_id="t1", organization_id="o1", project_id="p1", cost_entry_id="e1",
        status=ProjectCostEntryStatus.POSTED, occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="c2"))
    scope_codes = {hint.scope_code for hint in channel.notified}
    assert scope_codes == {COST_ENTRY_LIST_SCOPE_CODE, COST_ENTRY_ACTUALS_SCOPE_CODE}


@pytest.mark.parametrize(
    ("change_type", "expected_scope_codes"),
    (
        (CostEntryStatusChangeType.SUBMITTED, {COST_ENTRY_LIST_SCOPE_CODE}),
        (CostEntryStatusChangeType.APPROVED, {COST_ENTRY_LIST_SCOPE_CODE}),
        (CostEntryStatusChangeType.REJECTED, {COST_ENTRY_LIST_SCOPE_CODE}),
        (
            CostEntryStatusChangeType.POSTED,
            {COST_ENTRY_LIST_SCOPE_CODE, COST_ENTRY_ACTUALS_SCOPE_CODE},
        ),
    ),
)
def test_status_changed_maps_to_source_derived_targets(change_type, expected_scope_codes):
    channel = _fake_channel()
    handler = build_cost_entry_view_invalidation_handler(channel)
    event = CostEntryStatusChanged(
        tenant_id="t1", organization_id="o1", project_id="p1", cost_entry_id="e1",
        change_type=change_type, occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="c3"))
    assert {hint.scope_code for hint in channel.notified} == expected_scope_codes


def test_updated_and_removed_map_to_list_target_only():
    channel = _fake_channel()
    handler = build_cost_entry_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    handler(
        CostEntryUpdated(tenant_id="t1", organization_id="o1", project_id="p1", cost_entry_id="e1", occurred_at=now),
        DomainEventContext(correlation_id="c4"),
    )
    handler(
        CostEntryRemoved(tenant_id="t1", organization_id="o1", project_id="p1", cost_entry_id="e2", occurred_at=now),
        DomainEventContext(correlation_id="c5"),
    )
    assert {hint.scope_code for hint in channel.notified} == {COST_ENTRY_LIST_SCOPE_CODE}


def test_reversed_maps_to_both_list_and_actuals_targets():
    channel = _fake_channel()
    handler = build_cost_entry_view_invalidation_handler(channel)
    event = CostEntryReversed(
        tenant_id="t1", organization_id="o1", project_id="p1", cost_entry_id="e2",
        reverses_entry_id="e1", occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="c6"))
    assert {hint.scope_code for hint in channel.notified} == {
        COST_ENTRY_LIST_SCOPE_CODE, COST_ENTRY_ACTUALS_SCOPE_CODE
    }


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_cost_entry_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    event = CostEntryUpdated(
        tenant_id="t1", organization_id="o1", project_id="p1", cost_entry_id="e1", occurred_at=now
    )
    handler(event, DomainEventContext(correlation_id="same-tx"))
    handler(event, DomainEventContext(correlation_id="same-tx"))
    assert len(channel.notified) == 1, "same target within one transaction coalesces"

    handler(event, DomainEventContext(correlation_id="next-tx"))
    assert len(channel.notified) == 2, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real producer path -- direct commands, converged onto FinanceGovernanceUnitOfWork
# ---------------------------------------------------------------------------


def test_create_manual_entry_produces_exactly_one_list_hint(services):
    _, project, cost_code, _period = _setup(services)
    hints = _spy_hints(services)

    entry = _create_draft(services, project, cost_code)

    cost_hints = _cost_entry_hints(hints)
    assert len(cost_hints) == 1
    assert cost_hints[0].scope_code == COST_ENTRY_LIST_SCOPE_CODE
    assert cost_hints[0].entity_id == project.id
    assert entry.status == ProjectCostEntryStatus.DRAFT


def test_replay_create_produces_zero_hints(services):
    _, project, cost_code, _period = _setup(services)
    first = _create_draft(services, project, cost_code)
    hints = _spy_hints(services)

    replay = _create_draft(services, project, cost_code)

    assert replay.id == first.id
    assert _cost_entry_hints(hints) == []


def test_update_draft_produces_exactly_one_list_hint(services):
    organization = services["tenant_context_service"].get_active_organization()
    _, project, cost_code, _period = _setup(services)
    entry = _create_draft(services, project, cost_code)
    hints = _spy_hints(services)

    updated = services["cost_entry_service"].update_draft(
        entry.id,
        expected_version=entry.row_version,
        description="Revised description",
        amount=Decimal("150.00"),
        currency_code=organization.base_currency,
        transaction_date=date(2026, 1, 13),
        cost_code_id=cost_code.id,
    )

    cost_hints = _cost_entry_hints(hints)
    assert len(cost_hints) == 1
    assert cost_hints[0].scope_code == COST_ENTRY_LIST_SCOPE_CODE
    assert updated.amount == Decimal("150.00")


def test_delete_draft_produces_exactly_one_list_hint(services):
    _, project, cost_code, _period = _setup(services)
    entry = _create_draft(services, project, cost_code)
    hints = _spy_hints(services)

    services["cost_entry_service"].delete_draft(entry.id, expected_version=entry.row_version)

    cost_hints = _cost_entry_hints(hints)
    assert len(cost_hints) == 1
    assert cost_hints[0].scope_code == COST_ENTRY_LIST_SCOPE_CODE
    _, total = services["cost_entry_service"].list_for_project(project.id)
    assert total == 0


def test_submit_approve_post_progression_produces_source_derived_hints(services):
    _, project, cost_code, _period = _setup(services)
    entry = _create_draft(services, project, cost_code)
    service = services["cost_entry_service"]

    hints = _spy_hints(services)
    submitted = service.submit(entry.id, expected_version=entry.row_version)
    submit_hints = _cost_entry_hints(hints)
    assert [h.scope_code for h in submit_hints] == [COST_ENTRY_LIST_SCOPE_CODE]

    hints.clear()
    approval_result = service.approve(submitted.id, expected_version=submitted.row_version)
    approved = service.get_entry(submitted.id)
    approve_hints = _cost_entry_hints(hints)
    assert [h.scope_code for h in approve_hints] == [COST_ENTRY_LIST_SCOPE_CODE]

    hints.clear()
    posted = service.post(
        approved.id, expected_version=approved.row_version, posting_date=date(2026, 1, 15)
    )
    post_hints = {h.scope_code for h in _cost_entry_hints(hints)}
    assert post_hints == {COST_ENTRY_LIST_SCOPE_CODE, COST_ENTRY_ACTUALS_SCOPE_CODE}
    assert posted.status == ProjectCostEntryStatus.POSTED
    del approval_result


def test_reject_produces_exactly_one_list_hint(services):
    _, project, cost_code, _period = _setup(services)
    entry = _create_draft(services, project, cost_code)
    service = services["cost_entry_service"]
    submitted = service.submit(entry.id, expected_version=entry.row_version)

    hints = _spy_hints(services)
    rejected = service.reject(
        submitted.id, expected_version=submitted.row_version, notes="Needs correction"
    )
    reject_hints = _cost_entry_hints(hints)
    assert [h.scope_code for h in reject_hints] == [COST_ENTRY_LIST_SCOPE_CODE]
    assert rejected.status == ProjectCostEntryStatus.DRAFT
    assert rejected.rejection_notes == "Needs correction"


def test_reverse_produces_both_list_and_actuals_hints(services):
    _, project, cost_code, _period = _setup(services)
    entry = _create_draft(services, project, cost_code)
    service = services["cost_entry_service"]
    submitted = service.submit(entry.id, expected_version=entry.row_version)
    service.approve(submitted.id, expected_version=submitted.row_version)
    approved = service.get_entry(submitted.id)
    posted = service.post(
        approved.id, expected_version=approved.row_version, posting_date=date(2026, 1, 15)
    )

    hints = _spy_hints(services)
    reversal = service.reverse(
        posted.id, expected_version=posted.row_version, command_id="p37-reverse-1",
        posting_date=date(2026, 1, 20), reason="Correct duplicate",
    )
    reversal_hints = {h.scope_code for h in _cost_entry_hints(hints)}
    assert reversal_hints == {COST_ENTRY_LIST_SCOPE_CODE, COST_ENTRY_ACTUALS_SCOPE_CODE}
    assert reversal.reverses_entry_id == posted.id


# ---------------------------------------------------------------------------
# Transaction correctness -- audit failure rolls back and leaves session usable
# ---------------------------------------------------------------------------


def test_audit_failure_rolls_back_and_leaves_the_session_usable(services, monkeypatch):
    """The direct commands now run inside `FinanceGovernanceCommandBoundary.cost_entry()`, whose
    UoW factory constructs a fresh `EnterpriseAuditService` per transaction (the same
    already-established characteristic every other governed Finance family shares). A failed
    audit call raises and produces zero postcommit hints; the shared session must remain usable
    for a subsequent legitimate operation afterward -- proof no session poisoning occurs."""
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    _, project, cost_code, _period = _setup(services)

    original_record = EnterpriseAuditService.record

    def _fail_cost_audit(self, **kwargs):
        if kwargs.get("entity_type") == "project_cost_entry":
            raise RuntimeError("simulated cost audit failure")
        return original_record(self, **kwargs)

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_cost_audit)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        _create_draft(services, project, cost_code, command_id="p37-audit-fail")
    assert _cost_entry_hints(hints) == []

    monkeypatch.undo()
    recovered = _create_draft(services, project, cost_code, command_id="p37-audit-recovered")
    assert recovered.amount == Decimal("100.00"), (
        "the shared session must remain usable for a subsequent legitimate operation"
    )


# ---------------------------------------------------------------------------
# Concurrency -- preserved, unweakened
# ---------------------------------------------------------------------------


def test_concurrent_update_draft_second_writer_rejected(services, session):
    """The pre-existing `expected_row_version` optimistic-concurrency guard on `ProjectCostEntry`
    is exercised directly at the repository layer, unchanged by P37's transaction-convergence
    work."""
    from sqlalchemy.orm import sessionmaker

    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.cost_entries.cost_entry import (
        SqlAlchemyProjectCostEntryRepository,
    )

    _, project, cost_code, _period = _setup(services)
    entry = _create_draft(services, project, cost_code)
    assert entry.row_version == 1

    repo_a = SqlAlchemyProjectCostEntryRepository(session)
    repo_a._tenant_context_service = services["tenant_context_service"]
    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        repo_b = SqlAlchemyProjectCostEntryRepository(session_b)
        repo_b._tenant_context_service = services["tenant_context_service"]
        read_by_a = repo_a.get(entry.id)
        read_by_b = repo_b.get(entry.id)
        assert read_by_a.row_version == read_by_b.row_version == 1

        read_by_a.description = "Writer A wins"
        repo_a.update(read_by_a, expected_row_version=1)
        session.commit()

        read_by_b.description = "Writer B loses"
        with pytest.raises(ConcurrencyError):
            repo_b.update(read_by_b, expected_row_version=1)
        session_b.rollback()
    finally:
        session_b.close()

    final = repo_a.get(entry.id)
    assert final.description == "Writer A wins", "the losing writer's change must not persist"


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow per-target destination invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_cost_entry_list_stale_invalidates_costs_only(services):
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onCostEntryListStale("proj-a")
    assert controller._invalidated_destinations == {"costs"}

    controller._invalidated_destinations.clear()
    controller.onCostEntryListStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"


def test_financials_controller_cost_entry_actuals_stale_invalidates_the_legacy_four_minus_costs(
    services,
):
    """Preserves the legacy signal's own 4-destination fan-out (overview/costs/performance/
    commercial) -- `costs` is covered by the separate list-target hint every fact already emits,
    so the actuals binder only needs to add overview/performance/commercial."""
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onCostEntryActualsStale("proj-a")
    assert controller._invalidated_destinations == {"overview", "performance", "commercial"}

    controller._invalidated_destinations.clear()
    controller.onCostEntryActualsStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"
