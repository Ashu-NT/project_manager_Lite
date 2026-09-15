"""centralized navigation accessibility -- shell navigation must
consume the SAME authoritative accessible-module policy Global Overview's
module cards and Quick Actions already use (PlatformRuntimeApplicationService
.list_accessible_modules()), never a second copy of that rule."""

from __future__ import annotations

from src.core.platform.api.desktop.models.common import DesktopApiError, DesktopApiResult
from src.core.platform.api.desktop.platform_runtime.models.runtime import ModuleDto
from src.ui_qml.shell.context import ShellContext
from src.ui_qml.shell.navigation import (
    NavigationItemViewModel,
    filter_navigation_items,
    is_navigation_item_accessible,
)
from src.ui_qml.shell.navigation_accessibility import NavigationAccessibilityCoordinator
from src.ui_qml.shell.presenters.navigation.navigation_accessibility_presenter import (
    NavigationAccessibilityPresenter,
)


def _item(route_id: str, module_code: str, *, module_label: str = "") -> NavigationItemViewModel:
    return NavigationItemViewModel(
        route_id=route_id,
        module_code=module_code,
        module_label=module_label or module_code,
        group_label="Workspaces",
        title=route_id,
        qml_source=f"file:///dummy/{route_id}.qml",
    )


_OVERVIEW = _item("shell.home", "shell")
_PLATFORM = _item("platform.workspace", "platform")
_PM = _item("project_management.workspace", "project_management")
_ALL_ITEMS = [_OVERVIEW, _PLATFORM, _PM]


class _FakePlatformRuntimeApi:
    def __init__(self, *, accessible_codes: tuple[str, ...] | None, ok: bool = True) -> None:
        self._accessible_codes = accessible_codes
        self._ok = ok

    def list_accessible_modules(self) -> DesktopApiResult[tuple[ModuleDto, ...]]:
        if not self._ok:
            return DesktopApiResult(
                ok=False, error=DesktopApiError(code="X", message="boom", category="domain")
            )
        modules = tuple(
            ModuleDto(
                code=code,
                label=code,
                description="",
                default_enabled=True,
                stage="ga",
                primary_capabilities=(),
            )
            for code in (self._accessible_codes or ())
        )
        return DesktopApiResult(ok=True, data=modules)


# -- Pure projection: is_navigation_item_accessible / filter_navigation_items ------------------


def test_overview_always_accessible_regardless_of_accessible_modules():
    assert is_navigation_item_accessible("shell", accessible_module_codes=frozenset())


def test_platform_always_accessible_even_when_not_in_accessible_modules():
    assert is_navigation_item_accessible("platform", accessible_module_codes=frozenset())


def test_pm_accessible_only_when_in_accessible_modules():
    assert not is_navigation_item_accessible(
        "project_management", accessible_module_codes=frozenset()
    )
    assert is_navigation_item_accessible(
        "project_management", accessible_module_codes=frozenset({"project_management"})
    )


def test_unknown_module_code_is_hidden_by_default():
    assert not is_navigation_item_accessible(
        "some_future_module", accessible_module_codes=frozenset({"project_management"})
    )


def test_filter_navigation_items_keeps_shell_and_platform_and_hides_inaccessible_pm():
    filtered = filter_navigation_items(_ALL_ITEMS, accessible_module_codes=frozenset())
    assert [item.route_id for item in filtered] == ["shell.home", "platform.workspace"]


def test_filter_navigation_items_shows_pm_when_accessible():
    filtered = filter_navigation_items(
        _ALL_ITEMS, accessible_module_codes=frozenset({"project_management"})
    )
    assert [item.route_id for item in filtered] == [
        "shell.home",
        "platform.workspace",
        "project_management.workspace",
    ]


def test_filter_navigation_items_preserves_existing_order_for_accessible_routes():
    reordered_source = [_PM, _OVERVIEW, _PLATFORM]
    filtered = filter_navigation_items(
        reordered_source, accessible_module_codes=frozenset({"project_management"})
    )
    assert [item.route_id for item in filtered] == [
        "project_management.workspace",
        "shell.home",
        "platform.workspace",
    ]


# -- NavigationAccessibilityPresenter (fails closed) --------------------------------------------


def test_presenter_returns_empty_set_when_api_is_none():
    presenter = NavigationAccessibilityPresenter(platform_runtime_api=None)
    assert presenter.load_accessible_module_codes() == frozenset()


def test_presenter_returns_empty_set_when_api_call_fails():
    presenter = NavigationAccessibilityPresenter(
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=None, ok=False)
    )
    assert presenter.load_accessible_module_codes() == frozenset()


def test_presenter_returns_accessible_codes_on_success():
    presenter = NavigationAccessibilityPresenter(
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=("project_management",))
    )
    assert presenter.load_accessible_module_codes() == frozenset({"project_management"})


# -- NavigationAccessibilityCoordinator: ShellContext integration -------------------------------


def _build_shell_context(*, current_route_id: str = "shell.home") -> ShellContext:
    context = ShellContext(
        app_title="Test",
        navigation_items=_ALL_ITEMS,
        current_route_id=current_route_id,
    )
    return context


def test_coordinator_refresh_filters_navigation_items_on_shell_context(qapp):
    context = _build_shell_context()
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context,
        presenter=NavigationAccessibilityPresenter(
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
        ),
        all_navigation_items=_ALL_ITEMS,
    )
    coordinator.refresh()

    route_ids = [item["routeId"] for item in context.navigationItems]
    assert route_ids == ["shell.home", "platform.workspace"]


def test_coordinator_scope_change_from_inaccessible_to_accessible_adds_pm_navigation(qapp):
    context = _build_shell_context()
    presenter = NavigationAccessibilityPresenter(
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
    )
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context, presenter=presenter, all_navigation_items=_ALL_ITEMS
    )
    coordinator.refresh()
    assert "project_management.workspace" not in [i["routeId"] for i in context.navigationItems]

    # Scope changed (e.g. organization switch) and PM is now accessible --
    # simulate by swapping the presenter's underlying api, then firing
    # scopeChanged exactly as app.py's real switchers do.
    coordinator._presenter = NavigationAccessibilityPresenter(  # noqa: SLF001
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=("project_management",))
    )
    context.scopeChanged.emit()

    assert "project_management.workspace" in [i["routeId"] for i in context.navigationItems]


def test_coordinator_scope_change_from_accessible_to_inaccessible_removes_pm_navigation(qapp):
    context = _build_shell_context()
    presenter = NavigationAccessibilityPresenter(
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=("project_management",))
    )
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context, presenter=presenter, all_navigation_items=_ALL_ITEMS
    )
    coordinator.refresh()
    assert "project_management.workspace" in [i["routeId"] for i in context.navigationItems]

    coordinator._presenter = NavigationAccessibilityPresenter(  # noqa: SLF001
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
    )
    context.scopeChanged.emit()

    assert "project_management.workspace" not in [i["routeId"] for i in context.navigationItems]


def test_no_restart_required_multiple_scope_changes_stay_in_sync(qapp):
    context = _build_shell_context()
    presenter = NavigationAccessibilityPresenter(
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
    )
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context, presenter=presenter, all_navigation_items=_ALL_ITEMS
    )
    coordinator.refresh()

    for accessible in (("project_management",), (), ("project_management",)):
        coordinator._presenter = NavigationAccessibilityPresenter(  # noqa: SLF001
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=accessible)
        )
        context.scopeChanged.emit()
        route_ids = [i["routeId"] for i in context.navigationItems]
        assert ("project_management.workspace" in route_ids) == bool(accessible)


# -- Current route invalidation ------------------------------------------------------------------


def test_user_on_pm_route_when_scope_change_makes_pm_inaccessible_is_returned_to_overview(qapp):
    context = _build_shell_context(current_route_id="shell.home")
    presenter = NavigationAccessibilityPresenter(
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=("project_management",))
    )
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context, presenter=presenter, all_navigation_items=_ALL_ITEMS
    )
    coordinator.refresh()
    context.selectRoute("project_management.workspace")
    assert context.currentRouteId == "project_management.workspace"

    coordinator._presenter = NavigationAccessibilityPresenter(  # noqa: SLF001
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
    )
    context.scopeChanged.emit()

    assert context.currentRouteId == "shell.home"


def test_user_on_platform_route_unaffected_when_pm_becomes_inaccessible(qapp):
    context = _build_shell_context(current_route_id="shell.home")
    presenter = NavigationAccessibilityPresenter(
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=("project_management",))
    )
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context, presenter=presenter, all_navigation_items=_ALL_ITEMS
    )
    coordinator.refresh()
    context.selectRoute("platform.workspace")

    coordinator._presenter = NavigationAccessibilityPresenter(  # noqa: SLF001
        platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
    )
    context.scopeChanged.emit()

    assert context.currentRouteId == "platform.workspace"


# -- Direct route selection (defense in depth) ---------------------------------------------------


def test_selecting_inaccessible_pm_route_directly_is_rejected(qapp):
    context = _build_shell_context(current_route_id="shell.home")
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context,
        presenter=NavigationAccessibilityPresenter(
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
        ),
        all_navigation_items=_ALL_ITEMS,
    )
    coordinator.refresh()

    context.selectRoute("project_management.workspace")

    assert context.currentRouteId == "shell.home"


def test_selecting_accessible_pm_route_directly_succeeds(qapp):
    context = _build_shell_context(current_route_id="shell.home")
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context,
        presenter=NavigationAccessibilityPresenter(
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=("project_management",))
        ),
        all_navigation_items=_ALL_ITEMS,
    )
    coordinator.refresh()

    context.selectRoute("project_management.workspace")

    assert context.currentRouteId == "project_management.workspace"


# -- Regression: Platform/Overview never filtered -------------------------------------------------


def test_platform_navigation_present_even_with_zero_accessible_enterprise_modules(qapp):
    context = _build_shell_context()
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context,
        presenter=NavigationAccessibilityPresenter(
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
        ),
        all_navigation_items=_ALL_ITEMS,
    )
    coordinator.refresh()

    route_ids = [item["routeId"] for item in context.navigationItems]
    assert "platform.workspace" in route_ids
    assert "shell.home" in route_ids


def test_api_failure_fails_closed_hides_pm_but_keeps_core_routes(qapp):
    context = _build_shell_context()
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context,
        presenter=NavigationAccessibilityPresenter(
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=None, ok=False)
        ),
        all_navigation_items=_ALL_ITEMS,
    )
    coordinator.refresh()

    route_ids = [item["routeId"] for item in context.navigationItems]
    assert route_ids == ["shell.home", "platform.workspace"]


# -- Consistency: nav, module cards, and Quick Actions must read the same policy ----------------


def test_navigation_and_global_overview_capabilities_read_the_identical_source_method():
    """Sidebar navigation, Global Overview's PM module card
    (ProjectManagementModuleOverviewContributor), and Quick Actions
    (GlobalOverviewService.get_capabilities) must never keep separate copies
    of "is PM accessible" -- all three call
    PlatformRuntimeApplicationService.list_accessible_modules(), never
    list_modules()/list_enabled_modules()/a role-name check. This is a static
    guard against future drift: if any of these call sites is later changed
    to a different method, this test fails and the change should be
    reconsidered rather than accepted as an independent, possibly-diverging
    policy copy."""
    import inspect

    from src.core.application.global_overview.services.global_overview_service import (
        GlobalOverviewService,
    )
    from src.core.modules.project_management.application.global_overview.pm_module_overview_contributor import (
        ProjectManagementModuleOverviewContributor,
    )

    nav_source = inspect.getsource(
        NavigationAccessibilityPresenter.load_accessible_module_codes
    )
    overview_capabilities_source = inspect.getsource(GlobalOverviewService.get_capabilities)
    pm_module_card_source = inspect.getsource(
        ProjectManagementModuleOverviewContributor._is_accessible
    )

    for source in (nav_source, overview_capabilities_source, pm_module_card_source):
        assert "list_accessible_modules" in source
        assert "list_modules(" not in source
        assert "list_enabled_modules(" not in source


# -- Global Navigation Tree stays in sync with the same filtered items -------------------------


def test_global_navigation_tree_reflects_filtered_navigation_items(qapp):
    context = _build_shell_context(current_route_id="shell.home")
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context,
        presenter=NavigationAccessibilityPresenter(
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=())
        ),
        all_navigation_items=_ALL_ITEMS,
    )
    coordinator.refresh()

    groups_by_id = {group["id"]: group for group in context.globalNavigation}
    business_route_ids = {item["routeId"] for item in groups_by_id.get("business", {}).get("items", [])}
    administration_route_ids = {item["routeId"] for item in groups_by_id["administration"]["items"]}

    assert "project_management.workspace" not in business_route_ids
    assert "platform.workspace" in administration_route_ids


def test_global_navigation_tree_adds_pm_when_scope_change_makes_it_accessible(qapp):
    context = _build_shell_context(current_route_id="shell.home")
    coordinator = NavigationAccessibilityCoordinator(
        shell_context=context,
        presenter=NavigationAccessibilityPresenter(
            platform_runtime_api=_FakePlatformRuntimeApi(accessible_codes=("project_management",))
        ),
        all_navigation_items=_ALL_ITEMS,
    )
    coordinator.refresh()

    groups_by_id = {group["id"]: group for group in context.globalNavigation}
    business_route_ids = {item["routeId"] for item in groups_by_id["business"]["items"]}
    assert "project_management.workspace" in business_route_ids


def test_current_module_code_reflects_selected_route(qapp):
    context = _build_shell_context(current_route_id="shell.home")
    assert context.currentModuleCode == "shell"

    context.selectRoute("platform.workspace")
    assert context.currentModuleCode == "platform"
