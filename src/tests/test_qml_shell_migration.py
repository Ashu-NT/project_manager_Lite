from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.login import LoginViewModel, ShellLoginController
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_engine import QML_IMPORT_ROOTS
from src.ui_qml.shell.qml_registry import QmlRouteRegistry, build_qml_route_registry
from src.ui_qml.shell.runtime_session import ShellRuntimeSessionController
from src.ui_qml.shell.routes import build_shell_routes


def test_qml_shell_routes_point_to_existing_qml_files() -> None:
    routes = build_shell_routes()

    assert [route.route_id for route in routes] == ["shell.app", "shell.home"]
    assert routes[0].qml_path.name == "App.qml"
    assert routes[1].qml_path.name == "HomeWorkspace.qml"
    assert all(route.qml_path.exists() for route in routes)


def test_qml_route_registry_rejects_duplicate_routes() -> None:
    route = build_shell_routes()[0]
    registry = QmlRouteRegistry([route])

    with pytest.raises(ValueError, match="already registered"):
        registry.register(route)


def test_qml_shell_navigation_view_models_are_built_from_registry() -> None:
    registry = build_qml_route_registry()
    items = build_main_window_navigation(registry)

    assert [(item.route_id, item.title) for item in items] == [
        ("shell.home", "QML Home"),
        ("platform.admin", "Admin Console"),
        ("platform.control", "Control Center"),
        ("platform.settings", "Settings"),
        ("project_management.projects", "Projects"),
        ("project_management.tasks", "Tasks"),
        ("project_management.scheduling", "Scheduling"),
        ("project_management.resources", "Resources"),
        ("project_management.financials", "Financials"),
        ("project_management.portfolio", "Portfolio"),
        ("project_management.register", "Register"),
        ("project_management.collaboration", "Collaboration"),
        ("project_management.timesheets", "Timesheets"),
        ("project_management.dashboard", "Dashboard"),
        ("inventory_procurement.dashboard", "Inventory Dashboard"),
        ("inventory_procurement.catalog", "Catalog"),
        ("inventory_procurement.inventory", "Inventory"),
        ("inventory_procurement.reservations", "Reservations"),
        ("inventory_procurement.procurement", "Procurement"),
        ("inventory_procurement.pricing", "Pricing"),
        ("inventory_procurement.movements", "Stock Movements"),
        ("inventory_procurement.warehouses", "Warehouses & Locations"),
        ("maintenance_management.dashboard", "Maintenance Dashboard"),
        ("maintenance_management.assets", "Assets"),
        ("maintenance_management.work_requests", "Work Requests"),
        ("maintenance_management.work_orders", "Work Orders"),
        ("maintenance_management.preventive", "Preventive"),
        ("maintenance_management.reliability", "Reliability"),
        ("maintenance_management.planner", "Planner"),
    ]


def test_qml_shell_context_exposes_navigation_for_qml_binding() -> None:
    registry = build_qml_route_registry()
    context = build_shell_context(build_main_window_navigation(registry))
    route_by_id = {route.route_id: route for route in registry.list_navigation_routes()}

    assert context.appTitle == "TECHASH Enterprise"
    assert context.currentRouteId == "shell.home"
    assert context.currentRouteSource == route_by_id["shell.home"].qml_path.as_uri()
    assert [item["routeId"] for item in context.navigationItems] == [
        "shell.home",
        "platform.admin",
        "platform.control",
        "platform.settings",
        "project_management.projects",
        "project_management.tasks",
        "project_management.scheduling",
        "project_management.resources",
        "project_management.financials",
        "project_management.portfolio",
        "project_management.register",
        "project_management.collaboration",
        "project_management.timesheets",
        "project_management.dashboard",
        "inventory_procurement.dashboard",
        "inventory_procurement.catalog",
        "inventory_procurement.inventory",
        "inventory_procurement.reservations",
        "inventory_procurement.procurement",
        "inventory_procurement.pricing",
        "inventory_procurement.movements",
        "inventory_procurement.warehouses",
        "maintenance_management.dashboard",
        "maintenance_management.assets",
        "maintenance_management.work_requests",
        "maintenance_management.work_orders",
        "maintenance_management.preventive",
        "maintenance_management.reliability",
        "maintenance_management.planner",
    ]
    assert context.navigationItems[0]["qmlSource"] == route_by_id["shell.home"].qml_path.as_uri()

    context.selectRoute("platform.admin")

    assert context.currentRouteId == "platform.admin"
    assert context.currentRouteSource == route_by_id["platform.admin"].qml_path.as_uri()

    context.selectRoute("platform.unknown")

    assert context.currentRouteId == "platform.admin"


def test_qml_shell_context_can_reload_active_route(qapp) -> None:
    registry = build_qml_route_registry()
    context = build_shell_context(build_main_window_navigation(registry))
    original_source = context.currentRouteSource
    emitted_sources: list[str] = []

    context.currentRouteSourceChanged.connect(lambda: emitted_sources.append(context.currentRouteSource))
    context.reloadCurrentRoute()
    qapp.processEvents()

    assert emitted_sources[0] == ""
    assert emitted_sources[-1] == original_source
    assert context.currentRouteSource == original_source


def test_qml_login_view_model_keeps_empty_credentials_by_default() -> None:
    view_model = LoginViewModel()

    assert view_model.username == ""
    assert view_model.password == ""
    assert view_model.error_message == ""
    assert not view_model.is_busy


def test_qml_login_controller_authenticates_and_updates_session(services) -> None:
    services["user_session"].clear()
    controller = ShellLoginController(
        auth_service=services["auth_service"],
        user_session=services["user_session"],
    )

    controller.setUsername("admin")
    controller.setPassword("ChangeMe123!")
    controller.signIn()

    assert controller.isAuthenticated is True
    assert controller.errorMessage == ""
    assert controller.password == ""
    assert services["user_session"].is_authenticated() is True


def test_qml_runtime_session_controller_reauthenticates_after_expiry(qapp, services) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    registry = build_qml_route_registry()
    shell_context = build_shell_context(build_main_window_navigation(registry))
    shell_context.selectRoute("project_management.tasks")
    reloaded_sources: list[str] = []
    refresh_markers: list[str] = []
    prompt_usernames: list[str | None] = []
    quit_markers: list[str] = []
    original_source = shell_context.currentRouteSource

    shell_context.currentRouteSourceChanged.connect(
        lambda: reloaded_sources.append(shell_context.currentRouteSource)
    )

    def _prompt(username: str | None) -> bool:
        prompt_usernames.append(username)
        authenticated_user = auth.authenticate(
            username or "admin",
            "ChangeMe123!",
            device_label="Runtime Reauth",
        )
        user_session.set_principal(auth.build_principal(authenticated_user))
        return True

    controller = ShellRuntimeSessionController(
        shell_context=shell_context,
        user_session=user_session,
        login_prompt=_prompt,
        refresh_callbacks=(lambda: refresh_markers.append("refreshed"),),
        quit_application=lambda: quit_markers.append("quit"),
        poll_interval_ms=1_000,
        app=qapp,
    )
    current_session_id = user_session.principal.session_id

    auth.revoke_session(current_session_id, note="expire runtime session")
    controller.revalidateSession()
    qapp.processEvents()

    assert prompt_usernames == ["admin"]
    assert refresh_markers == ["refreshed"]
    assert quit_markers == []
    assert user_session.is_authenticated() is True
    assert reloaded_sources[0] == ""
    assert reloaded_sources[-1] == original_source


def test_qml_runtime_session_controller_quits_when_reauth_is_rejected(qapp, services) -> None:
    auth = services["auth_service"]
    user_session = services["user_session"]
    shell_context = build_shell_context(build_main_window_navigation(build_qml_route_registry()))
    quit_markers: list[str] = []
    prompt_usernames: list[str | None] = []
    controller = ShellRuntimeSessionController(
        shell_context=shell_context,
        user_session=user_session,
        login_prompt=lambda username: prompt_usernames.append(username) or False,
        quit_application=lambda: quit_markers.append("quit"),
        poll_interval_ms=1_000,
        app=qapp,
    )
    current_session_id = user_session.principal.session_id

    auth.revoke_session(current_session_id, note="expire runtime session")
    controller.revalidateSession()

    assert prompt_usernames == ["admin"]
    assert quit_markers == ["quit"]


def test_qml_runtime_session_controller_revalidates_when_app_becomes_active(qapp, services) -> None:
    shell_context = build_shell_context(build_main_window_navigation(build_qml_route_registry()))
    controller = ShellRuntimeSessionController(
        shell_context=shell_context,
        user_session=services["user_session"],
        login_prompt=lambda _username: True,
        poll_interval_ms=1_000,
        app=qapp,
    )
    revalidate_markers: list[str] = []
    original_revalidate = controller.revalidateSession

    def _revalidate() -> None:
        revalidate_markers.append("called")
        original_revalidate()

    controller.revalidateSession = _revalidate  # type: ignore[method-assign]

    controller._on_application_state_changed(Qt.ApplicationState.ApplicationActive)

    assert revalidate_markers == ["called"]


def test_qml_engine_registers_named_import_roots() -> None:
    import_roots = {path.resolve() for path in QML_IMPORT_ROOTS}

    assert Path("src/ui_qml/shared/qml").resolve() in import_roots
    assert Path("src/ui_qml/platform/qml").resolve() in import_roots
    assert Path("src/ui_qml/modules/project_management/qml").resolve() in import_roots
    assert Path("src/ui_qml/modules/inventory_procurement/qml").resolve() in import_roots
    assert Path("src/ui_qml/modules/maintenance/qml").resolve() in import_roots


def test_qml_shell_replaces_widget_entrypoint() -> None:
    entrypoint = Path("main_qt.py").read_text(encoding="utf-8")

    assert "from src.ui_qml.shell.app import main" in entrypoint
    assert "src.ui.shell.app" not in entrypoint

