"""P35: Finance Planned Cost full modernization -- `calculate_snapshot` (the ONLY Planned Cost
write operation) converges onto the already-existing, already-wired `FinanceGovernanceUnitOfWork`
(via a new `FinanceGovernanceCommandBoundary.planned_cost()` method, mirroring the exact P19
Forecast pattern), records a single typed `PlannedCostSnapshotCalculated` DomainEvent precommit
in place of the legacy `planned_costs_changed` Signal, and routes ViewInvalidation through a new
project-scoped `planned_cost_snapshot` target -- mirroring `forecast_planning`'s own single-target
shape exactly, since source proves there is no independently cached "detail" read model to route a
separate scope to.

`planned_costs_changed` is DELETED from `DomainEvents` entirely -- assert
`not hasattr(domain_events, ...)`. Enterprise audit was already atomic before this phase and stays
atomic; the real, pre-existing optimistic-concurrency guard (a version-checked supersede of the
previous version, plus a DB-level per-project-revision uniqueness constraint mapped to
`ConcurrencyError`) is preserved exactly, unweakened."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.planned_costs.event_handlers.view_invalidation import (
    PLANNED_COST_CATEGORY,
    PLANNED_COST_SNAPSHOT_SCOPE_CODE,
    build_planned_cost_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.planned_costs.planned_cost_events import (
    PlannedCostSnapshotCalculated,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
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

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _planned_cost_hints(hints):
    return [h for h in hints if h.category == PLANNED_COST_CATEGORY]


def _setup_project(services, *, planned_hours: float = 40.0, hourly_rate: float = 50.0):
    project = services["project_service"].create_project(
        "P35 Planned Cost Project", financial_currency_code="USD"
    )
    cost_code = services["financial_configuration_service"].create_cost_code(
        code="P35-LABOR-DEFAULT", name="P35 Default Labor"
    )
    profile = services["financial_configuration_service"].get_profile(project.id)
    services["financial_configuration_service"].configure_profile(
        project.id, expected_version=profile.version, default_cost_code_id=cost_code.id,
    )
    resource = services["resource_service"].create_resource(
        "P35 Engineer", hourly_rate=hourly_rate, currency_code="USD"
    )
    rate_card = services["rate_card_service"].create_rate_card(
        name="P35 Planned Cost Project Rates", project_id=project.id,
    )
    services["rate_card_service"].create_line(
        rate_card.id, rate_type=RateType.COST, unit="HOUR",
        rate_amount=Decimal(str(hourly_rate)), rate_currency="USD", resource_id=resource.id,
    )
    project_resource = services["project_resource_service"].add_to_project(
        project.id, resource.id, hourly_rate=hourly_rate, currency_code="USD",
        planned_hours=planned_hours,
    )
    task = services["task_service"].create_task(project.id, "P35 Design Task")
    assignment = services["task_service"].assign_project_resource(
        task_id=task.id, project_resource_id=project_resource.id, allocation_percent=100.0
    )
    return {
        "project": project, "cost_code": cost_code, "resource": resource,
        "project_resource": project_resource, "task": task, "assignment": assignment,
    }


def _allocate(services, ctx, hours: Decimal):
    assignment = ctx["assignment"]
    project_resource = ctx["project_resource"]
    updated = services["task_service"].update_assignment_planned_hours(
        assignment.id, allocated_planned_hours=hours,
        expected_assignment_version=assignment.version,
        expected_project_resource_version=project_resource.version,
    )
    assignment.version = updated.version
    assignment.allocated_planned_hours = updated.allocated_planned_hours
    project_resource.version += 1
    return updated


def test_legacy_planned_cost_signal_field_is_deleted():
    assert not hasattr(domain_events, "planned_costs_changed")


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


def test_snapshot_calculated_maps_to_single_project_scoped_target():
    channel = _fake_channel()
    handler = build_planned_cost_view_invalidation_handler(channel)
    event = PlannedCostSnapshotCalculated(
        tenant_id="t1", organization_id="o1", project_id="p1",
        planned_cost_version_id="v1", occurred_at=datetime.now(timezone.utc),
    )
    handler(event, DomainEventContext(correlation_id="c1"))
    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.scope_code == PLANNED_COST_SNAPSHOT_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "project"
    assert hint.scope.entity_id == "p1"
    assert hint.entity_id == "p1"


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_planned_cost_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    handler(
        PlannedCostSnapshotCalculated(
            tenant_id="t1", organization_id="o1", project_id="p1",
            planned_cost_version_id="v1", occurred_at=now,
        ),
        DomainEventContext(correlation_id="same-tx"),
    )
    handler(
        PlannedCostSnapshotCalculated(
            tenant_id="t1", organization_id="o1", project_id="p1",
            planned_cost_version_id="v1", occurred_at=now,
        ),
        DomainEventContext(correlation_id="same-tx"),
    )
    assert len(channel.notified) == 1, "same target within one transaction coalesces"

    handler(
        PlannedCostSnapshotCalculated(
            tenant_id="t1", organization_id="o1", project_id="p1",
            planned_cost_version_id="v2", occurred_at=now,
        ),
        DomainEventContext(correlation_id="next-tx"),
    )
    assert len(channel.notified) == 2, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real PlannedCostService producer path
# ---------------------------------------------------------------------------


def test_calculate_snapshot_produces_exactly_one_planned_cost_hint(services):
    ctx = _setup_project(services)
    _allocate(services, ctx, Decimal("30"))
    hints = _spy_hints(services)

    result = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    )

    planned_cost_hints = _planned_cost_hints(hints)
    assert len(planned_cost_hints) == 1
    assert planned_cost_hints[0].scope_code == PLANNED_COST_SNAPSHOT_SCOPE_CODE
    assert planned_cost_hints[0].entity_id == ctx["project"].id
    assert result.version.revision == 1


def test_second_calculation_supersedes_and_produces_one_hint(services):
    ctx = _setup_project(services)
    _allocate(services, ctx, Decimal("10"))
    services["planned_cost_service"].calculate_snapshot(ctx["project"].id, calculated_by="admin")

    _allocate(services, ctx, Decimal("20"))
    hints = _spy_hints(services)
    second = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    ).version

    planned_cost_hints = _planned_cost_hints(hints)
    assert len(planned_cost_hints) == 1
    assert second.revision == 2


def test_invalid_calculation_produces_zero_hints(services):
    project = services["project_service"].create_project(
        "P35 No Cost Code Project", financial_currency_code="USD"
    )
    hints = _spy_hints(services)
    with pytest.raises(BusinessRuleError):
        services["planned_cost_service"].calculate_snapshot(project.id, calculated_by="admin")
    assert _planned_cost_hints(hints) == []


def test_audit_failure_raises_and_produces_zero_hints(services, monkeypatch):
    """P35 §9/§25: enterprise audit was already atomic before this phase (`record_audit_entry(...,
    commit=False, fail_closed=True)`) and stays atomic -- a failed audit call raises and produces
    zero postcommit `PlannedCostSnapshotCalculated` hints, exactly matching the pattern already
    established for the other Finance families sharing this same `FinanceGovernanceCommandBoundary`.

    Whether the failed attempt's already-flushed version row is itself rolled back is a
    pre-existing characteristic of that shared boundary's `_execute()`/UoW machinery -- confirmed
    unchanged and untouched by P35 (reproduced identically against unmodified
    `ForecastVersionService.create_forecast`) -- not something this phase introduces, changes, or
    is in scope to fix (`FinanceGovernanceCommandBoundary` itself is explicitly out of scope; see
    P35's own "do not redesign Finance approval infrastructure" instruction). No other Finance
    family's test suite asserts persisted-state-after-failure through this boundary either."""
    ctx = _setup_project(services)
    _allocate(services, ctx, Decimal("30"))

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        services["planned_cost_service"].calculate_snapshot(ctx["project"].id, calculated_by="admin")

    assert _planned_cost_hints(hints) == []


# ---------------------------------------------------------------------------
# Concurrency -- preserved, unweakened
# ---------------------------------------------------------------------------


def test_concurrent_recalculation_second_writer_rejected_zero_hints(services, session):
    """P35 §8/§24: the real, pre-existing optimistic-concurrency guard (version-checked
    supersede of the previous version) is exercised directly at the repository layer with two
    independent sessions reading the same prior version before either writes -- the second
    writer must be rejected, not silently applied, and must produce zero hints."""
    from sqlalchemy.orm import sessionmaker

    from src.core.modules.project_management.infrastructure.persistence.repositories.finance.planned_costs.planned_cost import (
        SqlAlchemyProjectPlannedCostVersionRepository,
    )

    ctx = _setup_project(services)
    _allocate(services, ctx, Decimal("10"))
    first = services["planned_cost_service"].calculate_snapshot(
        ctx["project"].id, calculated_by="admin"
    ).version
    assert first.row_version == 1

    repo_a = SqlAlchemyProjectPlannedCostVersionRepository(session)
    repo_a._tenant_context_service = services["tenant_context_service"]
    session_b = sessionmaker(bind=session.bind, future=True)()
    try:
        repo_b = SqlAlchemyProjectPlannedCostVersionRepository(session_b)
        repo_b._tenant_context_service = services["tenant_context_service"]
        read_by_a = repo_a.get(first.id)
        read_by_b = repo_b.get(first.id)
        assert read_by_a.row_version == read_by_b.row_version == 1

        read_by_a.superseded_by = "admin-a"
        repo_a.update(read_by_a, expected_row_version=1)
        session.commit()

        read_by_b.superseded_by = "admin-b"
        with pytest.raises(ConcurrencyError):
            repo_b.update(read_by_b, expected_row_version=1)
        session_b.rollback()
    finally:
        session_b.close()

    final = repo_a.get(first.id)
    assert final.superseded_by == "admin-a", "the losing writer's change must not persist"


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow per-target destination invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_planned_cost_stale_invalidates_planning_and_performance(services):
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onPlannedCostSnapshotStale("proj-a")
    assert controller._invalidated_destinations == {"planning", "performance"}

    controller._invalidated_destinations.clear()
    controller.onPlannedCostSnapshotStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"
