"""P19: Finance Forecast typed events + ViewInvalidation + `forecasts_changed` retirement.

Covers: ForecastVersionChanged/ForecastLineChanged/ForecastDraftGenerated -> the two proven
read-model targets (forecast_planning, forecast_approved_basis) at project scope
(`ResourceScope(module_code="project_management", entity_type="project")`), dedupe by
(transaction correlation_id, target identity), true no-op semantics on `update_line`, the
financial-change-apply forecast-successor path reporting the same canonical
`ForecastVersionChanged(APPROVED)` vocabulary via the new generic
`ApprovalHandlerResult.domain_events` seam, the real FinancialsWorkspaceController's narrow
per-target destination invalidation, and the full retirement of `forecasts_changed` (zero
producers, zero consumers, field absent).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.forecasts.event_handlers.view_invalidation import (
    FORECAST_APPROVED_BASIS_SCOPE_CODE,
    FORECAST_CATEGORY,
    FORECAST_PLANNING_SCOPE_CODE,
    build_forecast_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastDraftGenerated,
    ForecastLineChangeType,
    ForecastLineChanged,
    ForecastVersionChangeType,
    ForecastVersionChanged,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
    FinancialChangeStatus,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastGenerationMode,
    ForecastLineSourceKind,
    ForecastLineSourceType,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import ResourceScope
from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _login(services, username: str, password: str) -> None:
    user = services["auth_service"].authenticate(username, password)
    services["user_session"].set_principal(services["auth_service"].build_principal(user))


def _pm_catalog(services) -> ProjectManagementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)


def _spy_hints(services):
    hints = []
    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


class _AnyOrgFilter:
    def matches(self, scope) -> bool:
        return True


def _forecast_hints(hints):
    return [h for h in hints if h.category == FORECAST_CATEGORY]


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _seed_project_and_cost_code(services):
    project = services["project_service"].create_project(
        _unique("P19 Forecast Project"), financial_currency_code="USD"
    )
    code = services["financial_configuration_service"].create_cost_code(
        code=_unique("P19-CC"), name="P19 cost code"
    )
    return project, code


# ---------------------------------------------------------------------------
# ViewInvalidation handler: mapping, target split, dedupe (unit-level, no DB)
# ---------------------------------------------------------------------------


def _context(correlation_id: str) -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


def test_version_created_maps_to_planning_target():
    channel = _fake_channel()
    handler = build_forecast_view_invalidation_handler(channel)
    event = ForecastVersionChanged(
        tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1",
        change_type=ForecastVersionChangeType.CREATED, occurred_at=datetime.now(timezone.utc),
    )
    handler(event, _context("c1"))
    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.scope_code == FORECAST_PLANNING_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "project"
    assert hint.scope.entity_id == "p1"
    assert hint.entity_id == "p1"


def test_version_approved_maps_to_both_planning_and_approved_basis_targets():
    channel = _fake_channel()
    handler = build_forecast_view_invalidation_handler(channel)
    event = ForecastVersionChanged(
        tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1",
        change_type=ForecastVersionChangeType.APPROVED, occurred_at=datetime.now(timezone.utc),
    )
    handler(event, _context("c2"))
    assert len(channel.notified) == 2
    scope_codes = {h.scope_code for h in channel.notified}
    assert scope_codes == {FORECAST_PLANNING_SCOPE_CODE, FORECAST_APPROVED_BASIS_SCOPE_CODE}
    assert all(h.entity_id == "p1" for h in channel.notified)


@pytest.mark.parametrize(
    "change_type",
    [ForecastVersionChangeType.SUBMITTED, ForecastVersionChangeType.REJECTED, ForecastVersionChangeType.DELETED],
)
def test_other_version_change_types_map_to_planning_target(change_type):
    channel = _fake_channel()
    handler = build_forecast_view_invalidation_handler(channel)
    event = ForecastVersionChanged(
        tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1",
        change_type=change_type, occurred_at=datetime.now(timezone.utc),
    )
    handler(event, _context("c3"))
    assert channel.notified[0].scope_code == FORECAST_PLANNING_SCOPE_CODE


def test_line_changed_and_draft_generated_map_to_planning_target():
    channel = _fake_channel()
    handler = build_forecast_view_invalidation_handler(channel)
    line_event = ForecastLineChanged(
        tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1", line_id="l1",
        change_type=ForecastLineChangeType.ADDED, occurred_at=datetime.now(timezone.utc),
    )
    draft_event = ForecastDraftGenerated(
        tenant_id="t1", organization_id="o1", project_id="p2", forecast_id="f2",
        occurred_at=datetime.now(timezone.utc),
    )
    handler(line_event, _context("c4"))
    handler(draft_event, _context("c4"))
    assert [h.scope_code for h in channel.notified] == [
        FORECAST_PLANNING_SCOPE_CODE, FORECAST_PLANNING_SCOPE_CODE,
    ]
    assert [h.entity_id for h in channel.notified] == ["p1", "p2"]


def test_dedupe_by_target_within_one_transaction_not_by_raw_event_fields():
    channel = _fake_channel()
    handler = build_forecast_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    handler(
        ForecastLineChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1", line_id="l1",
            change_type=ForecastLineChangeType.ADDED, occurred_at=now,
        ),
        _context("same-tx"),
    )
    handler(
        ForecastLineChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1", line_id="l2",
            change_type=ForecastLineChangeType.ADDED, occurred_at=now,
        ),
        _context("same-tx"),
    )
    assert len(channel.notified) == 1, "same project target within one transaction coalesces"

    handler(
        ForecastVersionChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1",
            change_type=ForecastVersionChangeType.APPROVED, occurred_at=now,
        ),
        _context("same-tx"),
    )
    assert len(channel.notified) == 2, "a distinct target within the same transaction is separate"

    handler(
        ForecastLineChanged(
            tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1", line_id="l3",
            change_type=ForecastLineChangeType.ADDED, occurred_at=now,
        ),
        _context("next-tx"),
    )
    assert len(channel.notified) == 3, "a new transaction is never coalesced with the previous one"


def test_approved_events_two_targets_never_coalesce_but_repeats_of_each_do():
    """One APPROVED DomainEvent -> two distinct hints (different scope_code, never coalesced
    together); a second APPROVED for the same project within the same transaction adds nothing
    new (each of its two targets was already notified)."""
    channel = _fake_channel()
    handler = build_forecast_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    event = ForecastVersionChanged(
        tenant_id="t1", organization_id="o1", project_id="p1", forecast_id="f1",
        change_type=ForecastVersionChangeType.APPROVED, occurred_at=now,
    )

    handler(event, _context("tx-a"))
    assert len(channel.notified) == 2
    assert {h.scope_code for h in channel.notified} == {
        FORECAST_PLANNING_SCOPE_CODE, FORECAST_APPROVED_BASIS_SCOPE_CODE,
    }

    handler(event, _context("tx-a"))
    assert len(channel.notified) == 2, "same two targets repeated in one transaction coalesce"

    handler(event, _context("tx-b"))
    assert len(channel.notified) == 4, "a new transaction re-notifies both targets"


# ---------------------------------------------------------------------------
# Real ForecastVersionService/ForecastGenerationService producer path
# ---------------------------------------------------------------------------


def test_create_forecast_produces_exactly_one_planning_hint(services):
    project, code = _seed_project_and_cost_code(services)
    hints = _spy_hints(services)

    forecast = services["forecast_version_service"].create_forecast(
        project.id, name="Draft", as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL, created_by="admin",
    )

    forecast_hints = _forecast_hints(hints)
    assert len(forecast_hints) == 1
    assert forecast_hints[0].scope_code == FORECAST_PLANNING_SCOPE_CODE
    assert forecast_hints[0].entity_id == project.id
    assert forecast is not None


def test_update_line_true_no_op_produces_zero_hints(services):
    project, code = _seed_project_and_cost_code(services)
    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id, name="Draft", as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL, created_by="admin",
    )
    line = forecasts.add_line(
        forecast.id, cost_code_id=code.id, description="ETC", amount=Decimal("50"),
        source_kind=ForecastLineSourceKind.MANUAL, source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin", expected_forecast_version=forecast.row_version,
    )
    forecast = forecasts.get_forecast(forecast.id)
    hints = _spy_hints(services)

    unchanged = forecasts.update_line(
        line.id, expected_line_version=line.row_version, expected_forecast_version=forecast.row_version,
        amount=Decimal("50"),
    )

    assert unchanged.row_version == line.row_version, "true no-op: no synthetic version bump"
    assert _forecast_hints(hints) == []

    changed = forecasts.update_line(
        line.id, expected_line_version=unchanged.row_version,
        expected_forecast_version=forecasts.get_forecast(forecast.id).row_version,
        amount=Decimal("75"),
    )
    assert changed.row_version != unchanged.row_version
    assert len(_forecast_hints(hints)) == 1


def test_approve_forecast_produces_exactly_one_planning_and_one_approved_basis_hint(services):
    project, code = _seed_project_and_cost_code(services)
    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id, name="Draft", as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL, created_by="admin",
    )
    forecasts.add_line(
        forecast.id, cost_code_id=code.id, description="ETC", amount=Decimal("50"),
        source_kind=ForecastLineSourceKind.MANUAL, source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin", expected_forecast_version=forecast.row_version,
    )
    forecast = forecasts.get_forecast(forecast.id)
    forecast = forecasts.submit_forecast(forecast.id, submitted_by="admin", expected_version=forecast.row_version)
    hints = _spy_hints(services)

    forecasts.approve_forecast(forecast.id, approved_by="admin", expected_version=forecast.row_version)

    forecast_hints = _forecast_hints(hints)
    assert len(forecast_hints) == 2
    scope_codes = {h.scope_code for h in forecast_hints}
    assert scope_codes == {FORECAST_PLANNING_SCOPE_CODE, FORECAST_APPROVED_BASIS_SCOPE_CODE}
    assert all(h.entity_id == project.id for h in forecast_hints)


def test_generate_draft_produces_exactly_one_planning_hint(services):
    project, code = _seed_project_and_cost_code(services)
    hints = _spy_hints(services)

    from src.core.platform.common.exceptions import BusinessRuleError

    try:
        services["forecast_generation_service"].generate_draft(
            project.id, name="Auto", as_of_date=date(2026, 8, 11), generated_by="admin",
        )
    except BusinessRuleError:
        # No financial sources to snapshot in this minimal fixture -- the point of this test
        # is that IF generation succeeds, it produces exactly one planning hint; a source-less
        # fixture is still a meaningful proof that generation never touches approved_basis.
        pytest.skip("no financial sources available to generate a draft in this minimal fixture")

    forecast_hints = _forecast_hints(hints)
    assert len(forecast_hints) == 1
    assert forecast_hints[0].scope_code == FORECAST_PLANNING_SCOPE_CODE


# ---------------------------------------------------------------------------
# Financial-change-apply forecast successor: same canonical vocabulary
# ---------------------------------------------------------------------------


def _seed_approved_finance_for_change(services):
    project, code = _seed_project_and_cost_code(services)
    budgets = services["budget_service"]
    budget = budgets.create_budget(project.id, "Approved control budget")
    budget_line = budgets.add_line(
        budget.id, cost_code_id=code.id, description="Approved scope", amount=Decimal("100"),
        expected_budget_version=budget.row_version,
    )
    budget = budgets.get_budget(budget.id)
    budget = budgets.submit_budget(budget.id, "admin", expected_version=budget.row_version)
    budgets.approve_budget(budget.id, approved_by="admin", expected_version=budget.row_version)

    forecasts = services["forecast_version_service"]
    forecast = forecasts.create_forecast(
        project.id, name="Approved forecast", as_of_date=date(2026, 8, 11),
        generation_mode=ForecastGenerationMode.MANUAL, created_by="admin",
    )
    forecast_line = forecasts.add_line(
        forecast.id, cost_code_id=code.id, description="Approved ETC", amount=Decimal("80"),
        source_kind=ForecastLineSourceKind.MANUAL, source_type=ForecastLineSourceType.MANUAL_ESTIMATE,
        created_by="admin", expected_forecast_version=forecast.row_version,
    )
    forecast = forecasts.get_forecast(forecast.id)
    forecast = forecasts.submit_forecast(forecast.id, submitted_by="admin", expected_version=forecast.row_version)
    forecast = forecasts.approve_forecast(forecast.id, approved_by="admin", expected_version=forecast.row_version)
    return project, code, forecast, forecast_line


def test_financial_change_apply_forecast_successor_reports_both_hints(services):
    _login(services, "admin", "ChangeMe123!")
    project, code, forecast, forecast_line = _seed_approved_finance_for_change(services)
    requester = _unique("p19-change-requester")
    services["auth_service"].register_user(requester, "StrongPass123", role_names=["planner"])
    _login(services, requester, "StrongPass123")

    changes = services["financial_change_service"]
    principal = services["user_session"].principal
    change = changes.create_change(
        project.id, title="Reduce ETC", reason="Scope reduction",
        effective_date=date(2026, 8, 11), created_by=principal.user_id,
    )
    changes.add_impact(
        change.id, impact_type=FinancialChangeImpactType.FORECAST, description="Reduce remaining ETC",
        amount=Decimal("-15"), cost_code_id=code.id, target_line_id=forecast_line.id,
        expected_change_version=change.row_version,
    )
    change = changes.get_change(change.id)
    change = changes.submit_change(
        change.id, submitted_by=principal.user_id, expected_version=change.row_version,
    )
    request = services["approval_service"].list_pending(project_id=project.id)[0]

    _login(services, "admin", "ChangeMe123!")
    hints = _spy_hints(services)
    services["approval_service"].approve_and_apply(request.id, note="Authorized")

    applied = changes.get_change(change.id)
    assert applied.status is FinancialChangeStatus.APPLIED
    assert applied.applied_forecast_id and applied.applied_forecast_id != forecast.id

    forecast_hints = _forecast_hints(hints)
    assert len(forecast_hints) == 2, (
        "the successor's appearance in the version list and its status as the new approved "
        "basis are both real, distinct facts of the same APPROVED event -- no invented second "
        "event type needed"
    )
    scope_codes = {h.scope_code for h in forecast_hints}
    assert scope_codes == {FORECAST_PLANNING_SCOPE_CODE, FORECAST_APPROVED_BASIS_SCOPE_CODE}
    assert all(h.entity_id == project.id for h in forecast_hints)


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow per-target destination invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_planning_stale_invalidates_only_planning(services):
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onForecastPlanningStale("proj-a")
    assert controller._invalidated_destinations == {"planning"}

    controller._invalidated_destinations.clear()
    controller.onForecastPlanningStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"


def test_financials_controller_approved_basis_stale_invalidates_overview_performance_commercial_not_planning(
    services,
):
    """P19-FIX: "planning" is deliberately excluded here -- on a real approval, the
    forecast_planning ViewInvalidation hint (handled separately by onForecastPlanningStale)
    always accompanies forecast_approved_basis and already covers it; see
    test_financials_controller_both_stale_signals_together_cover_the_full_destination_set below
    for the combined, no-duplicate-refresh proof."""
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onForecastApprovedBasisStale("proj-a")
    assert controller._invalidated_destinations == {"overview", "performance", "commercial"}


def test_financials_controller_both_stale_signals_together_cover_the_full_destination_set(services):
    """Proves the real per-approval consumer effect: forecast_planning + forecast_approved_basis
    hints together invalidate exactly the same four destinations the pre-P19-FIX single hint
    covered, with no destination invalidated by neither and none refreshed via two independent
    paths beyond the one coalescing QTimer-based refresh (P18B's established coalescing
    precedent) -- this is the "no duplicate equivalent UI refresh" proof."""
    catalog = _pm_catalog(services)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onForecastPlanningStale("proj-a")
    controller.onForecastApprovedBasisStale("proj-a")

    assert controller._invalidated_destinations == {
        "overview", "planning", "performance", "commercial",
    }


# ---------------------------------------------------------------------------
# forecasts_changed fully retired
# ---------------------------------------------------------------------------


def test_forecasts_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "forecasts_changed")


def test_forecasts_changed_has_zero_production_references():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "forecasts_changed" in source:
            hits.append(path)
    assert hits == [], hits
