"""P22: Finance Rate Card typed events + ViewInvalidation + `rates_changed` retirement.

Covers: RateCardCreated/RateCardDeactivated/RateCardLineAdded/RateCardLineUpdated/
RateCardLineDeactivated -> the two proven read-model targets (`rate_card_list`,
`OrganizationScope`; `rate_card_detail`, exact-card `ResourceScope`), the dual notification for
RateCardDeactivated (mirroring the P19-FIX correction), true no-op semantics on `update_line`,
dedupe by (transaction correlation_id, target identity), the new canonical
`FinanceGovernanceUnitOfWork.rate_cards` transaction boundary (Option A convergence -- no
separate UoW), the real FinancialsWorkspaceController's narrow "costs"-only destination
invalidation, and the full retirement of `rates_changed` (zero producers, zero consumers, field
absent).
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from src.core.modules.project_management.application.financials.rate_cards.event_handlers.view_invalidation import (
    RATE_CARD_CATEGORY,
    RATE_CARD_DETAIL_SCOPE_CODE,
    RATE_CARD_LIST_SCOPE_CODE,
    build_rate_card_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_events import (
    RateCardCreated,
    RateCardDeactivated,
    RateCardLineAdded,
    RateCardLineDeactivated,
    RateCardLineUpdated,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    RateLineOrigin,
    RateType,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import OrganizationScope, ResourceScope

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


def _rate_card_hints(hints):
    return [h for h in hints if h.category == RATE_CARD_CATEGORY]


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _context(correlation_id: str) -> DomainEventContext:
    return DomainEventContext(correlation_id=correlation_id)


# ---------------------------------------------------------------------------
# ViewInvalidation handler: mapping, dual notification, dedupe (unit-level, no DB)
# ---------------------------------------------------------------------------


def test_created_maps_to_list_target_only():
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", project_id=None, occurred_at=now,
        ),
        _context("c1"),
    )
    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.scope_code == RATE_CARD_LIST_SCOPE_CODE
    assert hint.category == RATE_CARD_CATEGORY
    assert isinstance(hint.scope, OrganizationScope)
    assert hint.entity_id == "c1"


def test_created_project_specific_maps_to_project_scoped_list_target():
    """P22-FIX: a project-specific card's list hint is a ResourceScope keyed on the project,
    not a plain OrganizationScope -- project identity travels only via the scope/entity_id."""
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", project_id="p1", occurred_at=now,
        ),
        _context("c1"),
    )
    assert len(channel.notified) == 1
    hint = channel.notified[0]
    assert hint.scope_code == RATE_CARD_LIST_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert not isinstance(hint.scope, OrganizationScope)
    assert hint.scope.module_code == "project_management"
    assert hint.scope.entity_type == "project"
    assert hint.scope.entity_id == "p1"
    assert hint.entity_id == "p1"


def test_deactivated_maps_to_both_list_and_detail_targets():
    """P19-FIX-style dual notification: deactivation changes both the list row AND, if
    selected, the detail's is_active field. Deactivation is for a project-specific card here,
    so the list hint (P22-FIX) is now a project-scoped ResourceScope, not OrganizationScope."""
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardDeactivated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", project_id="p1", occurred_at=now,
        ),
        _context("c1"),
    )
    assert len(channel.notified) == 2
    scope_codes = {h.scope_code for h in channel.notified}
    assert scope_codes == {RATE_CARD_LIST_SCOPE_CODE, RATE_CARD_DETAIL_SCOPE_CODE}

    list_hint = next(h for h in channel.notified if h.scope_code == RATE_CARD_LIST_SCOPE_CODE)
    assert isinstance(list_hint.scope, ResourceScope)
    assert list_hint.scope.entity_type == "project"
    assert list_hint.scope.entity_id == "p1"
    assert list_hint.entity_id == "p1"

    detail_hint = next(h for h in channel.notified if h.scope_code == RATE_CARD_DETAIL_SCOPE_CODE)
    assert isinstance(detail_hint.scope, ResourceScope)
    assert detail_hint.scope.module_code == "project_management"
    assert detail_hint.scope.entity_type == "rate_card"
    assert detail_hint.scope.entity_id == "c1"


def test_deactivated_org_wide_list_hint_stays_organization_scope():
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardDeactivated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", project_id=None, occurred_at=now,
        ),
        _context("c1"),
    )
    list_hint = next(h for h in channel.notified if h.scope_code == RATE_CARD_LIST_SCOPE_CODE)
    assert isinstance(list_hint.scope, OrganizationScope)
    assert list_hint.entity_id == "c1"


def test_project_a_and_project_b_list_hints_are_distinct_scopes():
    """Two different projects' cards in the same organization must produce two DISTINCT
    project-scoped list hints -- neither dedupes against the other, and neither is confused
    with an org-wide OrganizationScope hint (P22-FIX §7)."""
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="ca", project_id="project-a", occurred_at=now,
        ),
        _context("tx"),
    )
    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="cb", project_id="project-b", occurred_at=now,
        ),
        _context("tx"),
    )
    assert len(channel.notified) == 2
    entity_ids = {h.entity_id for h in channel.notified}
    assert entity_ids == {"project-a", "project-b"}


def test_org_wide_and_project_specific_list_hints_in_same_transaction_do_not_collapse():
    """An org-wide RateCardCreated and a project-A-specific RateCardCreated in the same
    transaction must produce ONE OrganizationScope hint AND ONE Project-A ResourceScope hint
    -- never collapsed into a single hint (P22-FIX §7)."""
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="c-org", project_id=None, occurred_at=now,
        ),
        _context("tx"),
    )
    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="c-proj-a", project_id="project-a", occurred_at=now,
        ),
        _context("tx"),
    )
    assert len(channel.notified) == 2
    org_hints = [h for h in channel.notified if isinstance(h.scope, OrganizationScope)]
    project_hints = [
        h for h in channel.notified
        if isinstance(h.scope, ResourceScope) and h.scope.entity_type == "project"
    ]
    assert len(org_hints) == 1
    assert len(project_hints) == 1
    assert project_hints[0].entity_id == "project-a"


def test_two_project_a_specific_changes_same_transaction_coalesce_to_one_list_hint():
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", project_id="project-a", occurred_at=now,
        ),
        _context("tx"),
    )
    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="c2", project_id="project-a", occurred_at=now,
        ),
        _context("tx"),
    )
    assert len(channel.notified) == 1, "same project-A list target within one transaction coalesces"


def test_line_events_map_to_detail_target_only():
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    for event in (
        RateCardLineAdded(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", rate_line_id="l1",
            project_id=None, occurred_at=now,
        ),
        RateCardLineUpdated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", rate_line_id="l1",
            project_id=None, occurred_at=now,
        ),
        RateCardLineDeactivated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", rate_line_id="l1",
            project_id=None, occurred_at=now,
        ),
    ):
        channel.notified.clear()
        handler(event, _context(_unique("tx")))
        assert len(channel.notified) == 1
        assert channel.notified[0].scope_code == RATE_CARD_DETAIL_SCOPE_CODE


def test_dedupe_by_target_within_one_transaction():
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardLineAdded(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", rate_line_id="l1",
            project_id=None, occurred_at=now,
        ),
        _context("same-tx"),
    )
    handler(
        RateCardLineUpdated(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", rate_line_id="l2",
            project_id=None, occurred_at=now,
        ),
        _context("same-tx"),
    )
    assert len(channel.notified) == 1, "same card detail target within one transaction coalesces"

    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o1", rate_card_id="c2", project_id=None, occurred_at=now,
        ),
        _context("same-tx"),
    )
    assert len(channel.notified) == 2, "a distinct target within the same transaction is separate"

    handler(
        RateCardLineAdded(
            tenant_id="t1", organization_id="o1", rate_card_id="c1", rate_line_id="l3",
            project_id=None, occurred_at=now,
        ),
        _context("next-tx"),
    )
    assert len(channel.notified) == 3, "a new transaction is never coalesced with the previous one"


def test_deactivated_two_targets_never_coalesce_but_repeats_of_each_do():
    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)
    event = RateCardDeactivated(
        tenant_id="t1", organization_id="o1", rate_card_id="c1", project_id="p1", occurred_at=now,
    )

    handler(event, _context("tx-a"))
    assert len(channel.notified) == 2

    handler(event, _context("tx-a"))
    assert len(channel.notified) == 2, "same two targets repeated in one transaction coalesce"

    handler(event, _context("tx-b"))
    assert len(channel.notified) == 4, "a new transaction re-notifies both targets"


def test_different_organization_project_scoped_hint_is_not_delivered_to_a_scoped_subscription():
    """A project-scoped rate_card_list hint for organization o2 must never be delivered to an
    ExactOrganization(o1) subscription -- ResourceScope is a strict refinement of
    OrganizationScope, still filtered by (tenant_id, organization_id) (P22-FIX §8)."""
    from src.core.shared.events.view_invalidation import ExactOrganization

    channel = _fake_channel()
    handler = build_rate_card_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        RateCardCreated(
            tenant_id="t1", organization_id="o2", rate_card_id="c1", project_id="project-a", occurred_at=now,
        ),
        _context("c1"),
    )
    hint = channel.notified[0]
    assert ExactOrganization("t1", "o1").matches(hint.scope) is False
    assert ExactOrganization("t1", "o2").matches(hint.scope) is True


# ---------------------------------------------------------------------------
# Real ProjectRateCardService producer path (governed FinanceGovernanceUnitOfWork)
# ---------------------------------------------------------------------------


def _create_card_and_line(services, **card_kwargs):
    rate_card_service = services["rate_card_service"]
    card = rate_card_service.create_rate_card(name=_unique("P22 Card"), **card_kwargs)
    line = rate_card_service.create_line(
        card.id,
        rate_type=RateType.COST,
        unit="HOUR",
        rate_amount=Decimal("50"),
        rate_currency="USD",
        origin=RateLineOrigin.CONFIGURED,
        resource_id=_unique("P22-RES"),
    )
    return card, line


def _seed_project(services):
    return services["project_service"].create_project(
        _unique("P22 Rate Card Project"), financial_currency_code="USD"
    )


def test_create_rate_card_produces_exactly_one_list_hint(services):
    hints = _spy_hints(services)

    rate_card_service = services["rate_card_service"]
    card = rate_card_service.create_rate_card(name=_unique("P22 Org Card"))

    rate_hints = _rate_card_hints(hints)
    assert len(rate_hints) == 1
    assert rate_hints[0].scope_code == RATE_CARD_LIST_SCOPE_CODE
    assert rate_hints[0].entity_id == card.id


def test_create_project_specific_rate_card_produces_project_scoped_list_hint(services):
    """P22-FIX real-service proof: a project-specific card's list hint is a project-keyed
    ResourceScope, matching the project it was created for."""
    project = _seed_project(services)
    hints = _spy_hints(services)

    rate_card_service = services["rate_card_service"]
    card = rate_card_service.create_rate_card(
        name=_unique("P22 Project Card"), project_id=project.id
    )

    rate_hints = _rate_card_hints(hints)
    assert len(rate_hints) == 1
    hint = rate_hints[0]
    assert hint.scope_code == RATE_CARD_LIST_SCOPE_CODE
    assert isinstance(hint.scope, ResourceScope)
    assert hint.scope.entity_type == "project"
    assert hint.scope.entity_id == project.id
    assert hint.entity_id == project.id
    assert card.project_id == project.id


def test_project_a_specific_deactivation_refreshes_project_a_list_not_project_b(services):
    """End-to-end proof of P22-FIX's central requirement: Project A's card change list-hint
    scope is distinct from Project B's -- a subscription scoped to Project B never matches it."""
    from src.core.shared.events.view_invalidation import ExactResource

    project_a = _seed_project(services)
    project_b = _seed_project(services)
    rate_card_service = services["rate_card_service"]
    card = rate_card_service.create_rate_card(
        name=_unique("P22 Project A Card"), project_id=project_a.id
    )
    hints = _spy_hints(services)

    rate_card_service.deactivate_rate_card(card.id, expected_version=card.version)

    rate_hints = _rate_card_hints(hints)
    list_hint = next(h for h in rate_hints if h.scope_code == RATE_CARD_LIST_SCOPE_CODE)
    assert list_hint.scope.entity_id == project_a.id

    project_b_filter = ExactResource(
        tenant_id=list_hint.scope.tenant_id,
        organization_id=list_hint.scope.organization_id,
        module_code=list_hint.scope.module_code,
        entity_type="project",
        entity_id=project_b.id,
    )
    assert project_b_filter.matches(list_hint.scope) is False, (
        "Project B's exact-resource subscription must not match Project A's list hint"
    )


def test_deactivate_rate_card_produces_both_hints(services):
    card, _line = _create_card_and_line(services)
    hints = _spy_hints(services)

    rate_card_service = services["rate_card_service"]
    deactivated = rate_card_service.deactivate_rate_card(card.id, expected_version=card.version)

    assert deactivated.is_active is False
    rate_hints = _rate_card_hints(hints)
    assert len(rate_hints) == 2
    assert {h.scope_code for h in rate_hints} == {RATE_CARD_LIST_SCOPE_CODE, RATE_CARD_DETAIL_SCOPE_CODE}


def test_deactivate_rate_card_true_no_op_produces_zero_hints(services):
    card, _line = _create_card_and_line(services)
    rate_card_service = services["rate_card_service"]
    deactivated = rate_card_service.deactivate_rate_card(card.id, expected_version=card.version)
    hints = _spy_hints(services)

    unchanged = rate_card_service.deactivate_rate_card(
        deactivated.id, expected_version=deactivated.version
    )

    assert unchanged.version == deactivated.version, "true no-op: no synthetic version bump"
    assert _rate_card_hints(hints) == []


def test_create_line_produces_exactly_one_detail_hint(services):
    card, _line = _create_card_and_line(services)
    hints = _spy_hints(services)

    rate_card_service = services["rate_card_service"]
    line = rate_card_service.create_line(
        card.id, rate_type=RateType.COST, unit="HOUR", rate_amount=Decimal("60"),
        rate_currency="USD", resource_id=_unique("P22-RES2"),
    )

    rate_hints = _rate_card_hints(hints)
    assert len(rate_hints) == 1
    assert rate_hints[0].scope_code == RATE_CARD_DETAIL_SCOPE_CODE
    assert rate_hints[0].entity_id == card.id
    assert line.rate_card_id == card.id


def test_update_line_true_no_op_produces_zero_hints(services):
    card, line = _create_card_and_line(services)
    rate_card_service = services["rate_card_service"]
    hints = _spy_hints(services)

    unchanged = rate_card_service.update_line(
        line.id, expected_version=line.version, rate_amount=line.rate_amount,
    )

    assert unchanged.version == line.version, "true no-op: no synthetic version bump"
    assert _rate_card_hints(hints) == []


def test_update_line_real_change_produces_exactly_one_detail_hint(services):
    card, line = _create_card_and_line(services)
    rate_card_service = services["rate_card_service"]
    hints = _spy_hints(services)

    updated = rate_card_service.update_line(
        line.id, expected_version=line.version, rate_amount=Decimal("75"),
    )

    assert updated.rate_amount == Decimal("75")
    rate_hints = _rate_card_hints(hints)
    assert len(rate_hints) == 1
    assert rate_hints[0].scope_code == RATE_CARD_DETAIL_SCOPE_CODE
    assert rate_hints[0].entity_id == card.id


def test_deactivate_line_produces_exactly_one_detail_hint(services):
    card, line = _create_card_and_line(services)
    rate_card_service = services["rate_card_service"]
    hints = _spy_hints(services)

    deactivated = rate_card_service.deactivate_line(line.id, expected_version=line.version)

    assert deactivated.is_active is False
    rate_hints = _rate_card_hints(hints)
    assert len(rate_hints) == 1
    assert rate_hints[0].scope_code == RATE_CARD_DETAIL_SCOPE_CODE


def test_deactivate_line_true_no_op_produces_zero_hints(services):
    card, line = _create_card_and_line(services)
    rate_card_service = services["rate_card_service"]
    deactivated = rate_card_service.deactivate_line(line.id, expected_version=line.version)
    hints = _spy_hints(services)

    unchanged = rate_card_service.deactivate_line(
        deactivated.id, expected_version=deactivated.version
    )

    assert unchanged.version == deactivated.version
    assert _rate_card_hints(hints) == []


def test_rate_card_uses_the_canonical_finance_governance_unit_of_work(services):
    """Option A convergence proof (P22 §3): Rate Card now shares the SAME canonical
    FinanceGovernanceUnitOfWork every other governed Finance capability uses -- no separate
    Rate Card UoW was created."""
    commands = services["finance_governance_commands"]
    seen_uows = []
    original_create = type(commands._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_uows.append(uow)
        return uow

    type(commands._uow_factory).create = _spy_create
    try:
        services["rate_card_service"].create_rate_card(name=_unique("P22 UoW Card"))
    finally:
        type(commands._uow_factory).create = original_create

    assert len(seen_uows) == 1
    assert hasattr(seen_uows[0], "rate_cards")
    assert hasattr(seen_uows[0], "forecasts"), "the SAME governance UoW class, not a new one"


# ---------------------------------------------------------------------------
# UI: FinancialsWorkspaceController narrow "costs"-only invalidation
# ---------------------------------------------------------------------------


def test_financials_controller_list_stale_invalidates_costs(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.financialsWorkspace
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onRateCardListStale("card-1")
    assert controller._invalidated_destinations == {"costs"}


def test_financials_controller_detail_stale_invalidates_costs_only_if_selected(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.financialsWorkspace
    controller._selected_rate_card_id = "card-1"
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onRateCardDetailStale("card-2")
    assert controller._invalidated_destinations == set(), "non-selected card must not invalidate"

    controller.onRateCardDetailStale("card-1")
    assert controller._invalidated_destinations == {"costs"}


def test_financials_controller_list_stale_for_project_invalidates_costs_only_if_selected_project(services):
    """P22-FIX: the project-scoped list stale path must be gated by the currently selected
    project, mirroring on_forecast_planning_stale's established pattern -- unlike the org-wide
    rateCardListStale path, which stays unconditional."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.financialsWorkspace
    controller._selected_project_id = "project-a"
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = lambda: None

    controller.onRateCardListStaleForProject("project-b")
    assert controller._invalidated_destinations == set(), "non-selected project must not invalidate"

    controller.onRateCardListStaleForProject("project-a")
    assert controller._invalidated_destinations == {"costs"}


def test_rate_card_adapter_dispatches_org_vs_project_list_hints_to_distinct_signals():
    """The Qt adapter itself must route an OrganizationScope rate_card_list hint to
    rateCardListStale and a project-scoped ResourceScope rate_card_list hint to
    rateCardListStaleForProject (P22-FIX)."""
    from src.core.shared.events.view_invalidation import OrganizationScope as _OrgScope
    from src.core.shared.events.view_invalidation import ResourceScope as _ResScope
    from src.core.shared.events.view_invalidation import ViewInvalidationHint as _Hint
    from src.ui_qml.modules.project_management.adapters.financials.rate_card_view_invalidation_adapter import (
        RateCardViewInvalidationAdapter,
    )

    adapter = RateCardViewInvalidationAdapter(channel=None, tenant_id="t1", organization_id="o1")
    org_calls = []
    project_calls = []
    adapter.rateCardListStale.connect(org_calls.append)
    adapter.rateCardListStaleForProject.connect(project_calls.append)

    adapter._on_hint(
        _Hint(
            scope=_OrgScope("t1", "o1"),
            category=RATE_CARD_CATEGORY,
            scope_code=RATE_CARD_LIST_SCOPE_CODE,
            entity_type="rate_card",
            entity_id="c1",
        )
    )
    adapter._on_hint(
        _Hint(
            scope=_ResScope(
                tenant_id="t1", organization_id="o1", module_code="project_management",
                entity_type="project", entity_id="project-a",
            ),
            category=RATE_CARD_CATEGORY,
            scope_code=RATE_CARD_LIST_SCOPE_CODE,
            entity_type="project",
            entity_id="project-a",
        )
    )

    assert org_calls == ["c1"]
    assert project_calls == ["project-a"]
    adapter.dispose()


# ---------------------------------------------------------------------------
# rates_changed fully retired
# ---------------------------------------------------------------------------


def test_rates_changed_field_no_longer_exists():
    assert not hasattr(domain_events, "rates_changed")


def test_rates_changed_has_zero_production_references():
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "rates_changed" in source:
            hits.append(path)
    assert hits == [], hits
