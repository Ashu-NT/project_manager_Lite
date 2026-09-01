"""P21: Finance Financial Setup typed events + ViewInvalidation + `financial_setup_changed`
retirement.

Covers: ProjectFinancialProfileUpdated/ProjectFinancialProfileTransitioned -> the sole proven
read-model target (`financial_profile`, project-scoped `ResourceScope`); CostCodeCreated/
CostCodeProfileUpdated/CostCodeActivated/CostCodeDeactivated/ProjectCostCodeRestrictionAdded/
ProjectCostCodeRestrictionRemoved recorded as canonical typed DomainEvents with deliberately NO
ViewInvalidation target (no cached cost-code projection exists anywhere in the Financials
workspace -- every cost-code picker is a live, on-demand query); true no-op semantics on
`configure_profile`/`update_cost_code`; dedupe by (transaction correlation_id, target identity);
the real FinancialsWorkspaceController's narrow "controls"-only destination invalidation; and the
full retirement of `financial_setup_changed` (zero producers, zero consumers, field absent).
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.project_management.application.financials.configuration_events import (
    CostCodeActivated,
    CostCodeCreated,
    CostCodeDeactivated,
    CostCodeProfileUpdated,
    ProjectCostCodeRestrictionAdded,
    ProjectCostCodeRestrictionRemoved,
    ProjectFinancialProfileTransitioned,
    ProjectFinancialProfileUpdated,
)
from src.core.modules.project_management.application.financials.event_handlers.view_invalidation import (
    FINANCIAL_PROFILE_SCOPE_CODE,
    FINANCIAL_SETUP_CATEGORY,
    build_financial_profile_view_invalidation_handler,
)
from src.core.modules.project_management.domain.financials.configuration import (
    BudgetControlMode,
    CostCodePolicy,
    FinancialProfileStatus,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import ResourceScope

_COUNTER = {"n": 0}


def _unique(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy_hints(services):
    hints = []
    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


class _AnyOrgFilter:
    def matches(self, scope) -> bool:
        return True


def _setup_hints(hints):
    return [h for h in hints if h.category == FINANCIAL_SETUP_CATEGORY]


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _context(correlation_id: str) -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


def _spy_events(services, *event_types):
    """Subscribes directly to the real post-commit bus for event types that have NO
    ViewInvalidation handler -- the only way to prove they are genuinely recorded (P21 §16)."""
    seen: list = []
    bus = services["finance_governance_commands"]._uow_factory._post_commit_bus
    for event_type in event_types:
        bus.subscribe(event_type, lambda event, _context, _seen=seen: _seen.append(event))
    return seen


def _seed_project(services):
    project = services["project_service"].create_project(
        _unique("P21 Finance Project"), financial_currency_code="USD"
    )
    return project


# ---------------------------------------------------------------------------
# ViewInvalidation handler: mapping, dedupe (unit-level, no DB)
# ---------------------------------------------------------------------------


def test_profile_updated_maps_to_financial_profile_target():
    channel = _fake_channel()
    handler = build_financial_profile_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        ProjectFinancialProfileUpdated(
            tenant_id="t1", organization_id="o1", project_id="p1", occurred_at=now,
        ),
        _context("c1"),
    )
    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.scope_code == FINANCIAL_PROFILE_SCOPE_CODE
    assert hint.category == FINANCIAL_SETUP_CATEGORY
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "project"
    assert hint.scope.entity_id == "p1"
    assert hint.entity_id == "p1"


def test_profile_transitioned_maps_to_financial_profile_target():
    channel = _fake_channel()
    handler = build_financial_profile_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        ProjectFinancialProfileTransitioned(
            tenant_id="t1", organization_id="o1", project_id="p1", status="ON_HOLD", occurred_at=now,
        ),
        _context("c1"),
    )
    assert len(channel.notified) == 1
    assert channel.notified[0].scope_code == FINANCIAL_PROFILE_SCOPE_CODE


def test_profile_dedupe_by_project_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_financial_profile_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        ProjectFinancialProfileUpdated(
            tenant_id="t1", organization_id="o1", project_id="p1", occurred_at=now,
        ),
        _context("same-tx"),
    )
    handler(
        ProjectFinancialProfileTransitioned(
            tenant_id="t1", organization_id="o1", project_id="p1", status="ACTIVE", occurred_at=now,
        ),
        _context("same-tx"),
    )
    assert len(channel.notified) == 1, "same project target within one transaction coalesces"

    handler(
        ProjectFinancialProfileUpdated(
            tenant_id="t1", organization_id="o1", project_id="p2", occurred_at=now,
        ),
        _context("same-tx"),
    )
    assert len(channel.notified) == 2, "a distinct project within the same transaction is separate"

    handler(
        ProjectFinancialProfileUpdated(
            tenant_id="t1", organization_id="o1", project_id="p1", occurred_at=now,
        ),
        _context("next-tx"),
    )
    assert len(channel.notified) == 3, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real FinancialConfigurationService producer path
# ---------------------------------------------------------------------------


def test_configure_profile_true_no_op_produces_zero_hints(services):
    project = _seed_project(services)
    setup = services["financial_configuration_service"]
    profile = setup.get_profile(project.id)
    hints = _spy_hints(services)

    unchanged = setup.configure_profile(
        project.id, expected_version=profile.version, currency_code=profile.currency_code,
    )

    assert unchanged.version == profile.version, "true no-op: no synthetic version bump"
    assert _setup_hints(hints) == []


def test_configure_profile_real_change_produces_exactly_one_financial_profile_hint(services):
    project = _seed_project(services)
    setup = services["financial_configuration_service"]
    profile = setup.get_profile(project.id)
    hints = _spy_hints(services)

    updated = setup.configure_profile(
        project.id, expected_version=profile.version,
        budget_control_mode=BudgetControlMode.BLOCK,
    )

    assert updated.budget_control_mode == BudgetControlMode.BLOCK
    setup_hints = _setup_hints(hints)
    assert len(setup_hints) == 1
    assert setup_hints[0].scope_code == FINANCIAL_PROFILE_SCOPE_CODE
    assert setup_hints[0].entity_id == project.id


def test_transition_profile_produces_exactly_one_financial_profile_hint(services):
    project = _seed_project(services)
    setup = services["financial_configuration_service"]
    profile = setup.get_profile(project.id)
    hints = _spy_hints(services)

    transitioned = setup.transition_profile(
        project.id, target=FinancialProfileStatus.ON_HOLD, expected_version=profile.version,
    )

    assert transitioned.status == FinancialProfileStatus.ON_HOLD
    setup_hints = _setup_hints(hints)
    assert len(setup_hints) == 1
    assert setup_hints[0].scope_code == FINANCIAL_PROFILE_SCOPE_CODE


def test_transition_profile_true_no_op_produces_zero_hints(services):
    project = _seed_project(services)
    setup = services["financial_configuration_service"]
    profile = setup.get_profile(project.id)
    hints = _spy_hints(services)

    unchanged = setup.transition_profile(
        project.id, target=profile.status, expected_version=profile.version,
    )

    assert unchanged.version == profile.version
    assert _setup_hints(hints) == []


def test_create_cost_code_records_typed_event_with_zero_view_invalidation_hints(services):
    """The only Financial Setup operation with a real, current production caller
    (`command_boundary.py`'s desktop-API `create_cost_code`) -- proven from source that no
    read-model in the Financials workspace caches cost-code data, so it correctly produces
    zero hints even though the typed event itself is genuinely recorded."""
    setup = services["financial_configuration_service"]
    events = _spy_events(services, CostCodeCreated)
    hints = _spy_hints(services)

    cost_code = setup.create_cost_code(code=_unique("P21-CC"), name="P21 Cost Code")

    assert len(events) == 1
    assert events[0].cost_code_id == cost_code.id
    assert _setup_hints(hints) == []


def test_update_cost_code_true_no_op_records_zero_events(services):
    setup = services["financial_configuration_service"]
    cost_code = setup.create_cost_code(code=_unique("P21-CC"), name="P21 Cost Code")
    events = _spy_events(services, CostCodeProfileUpdated)

    unchanged = setup.update_cost_code(
        cost_code.id, expected_version=cost_code.version, name="P21 Cost Code",
    )

    assert unchanged.version == cost_code.version, "true no-op: no synthetic version bump"
    assert events == []


def test_update_cost_code_real_change_records_exactly_one_event(services):
    setup = services["financial_configuration_service"]
    cost_code = setup.create_cost_code(code=_unique("P21-CC"), name="P21 Cost Code")
    events = _spy_events(services, CostCodeProfileUpdated)

    updated = setup.update_cost_code(
        cost_code.id, expected_version=cost_code.version, name="Renamed Cost Code",
    )

    assert updated.name == "Renamed Cost Code"
    assert len(events) == 1
    assert events[0].cost_code_id == cost_code.id


def test_activate_and_deactivate_cost_code_record_typed_events_with_zero_hints(services):
    setup = services["financial_configuration_service"]
    cost_code = setup.create_cost_code(code=_unique("P21-CC"), name="P21 Cost Code")
    events = _spy_events(services, CostCodeDeactivated, CostCodeActivated)
    hints = _spy_hints(services)

    deactivated = setup.deactivate_cost_code(cost_code.id, expected_version=cost_code.version)
    reactivated = setup.activate_cost_code(deactivated.id, expected_version=deactivated.version)

    assert deactivated.is_active is False
    assert reactivated.is_active is True
    assert [type(e).__name__ for e in events] == ["CostCodeDeactivated", "CostCodeActivated"]
    assert _setup_hints(hints) == []


def test_add_and_remove_project_cost_code_restriction_record_typed_events_with_zero_hints(services):
    project = _seed_project(services)
    setup = services["financial_configuration_service"]
    setup.configure_profile(
        project.id,
        expected_version=setup.get_profile(project.id).version,
        cost_code_policy=CostCodePolicy.RESTRICTED,
    )
    cost_code = setup.create_cost_code(code=_unique("P21-CC"), name="P21 Cost Code")
    events = _spy_events(
        services, ProjectCostCodeRestrictionAdded, ProjectCostCodeRestrictionRemoved
    )
    hints = _spy_hints(services)

    setup.add_project_cost_code(project_id=project.id, cost_code_id=cost_code.id)
    removed = setup.remove_project_cost_code(project_id=project.id, cost_code_id=cost_code.id)

    assert removed is True
    assert [type(e).__name__ for e in events] == [
        "ProjectCostCodeRestrictionAdded", "ProjectCostCodeRestrictionRemoved",
    ]
    assert _setup_hints(hints) == []


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow "controls"-only invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_financial_profile_stale_invalidates_only_controls(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.financialsWorkspace
    controller._set_selected_project_id("proj-a")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onFinancialProfileStale("proj-a")
    assert controller._invalidated_destinations == {"controls"}, (
        "narrower than the legacy {planning, costs, controls} -- no cached cost-code or "
        "planning/costs projection actually depends on Financial Setup facts"
    )

    controller._invalidated_destinations.clear()
    controller.onFinancialProfileStale("proj-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"


# ---------------------------------------------------------------------------
# financial_setup_changed fully retired
# ---------------------------------------------------------------------------


def test_financial_setup_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "financial_setup_changed")


def test_financial_setup_changed_has_zero_production_references():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "financial_setup_changed" in source:
            hits.append(path)
    assert hits == [], hits
