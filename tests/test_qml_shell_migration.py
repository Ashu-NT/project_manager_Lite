from pathlib import Path

import pytest

from src.ui_qml.shell.context import build_shell_context
from src.ui_qml.shell.login import LoginViewModel
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_registry import QmlRouteRegistry, build_qml_route_registry
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
        ("project_management.risk", "Risk"),
        ("project_management.portfolio", "Portfolio"),
        ("project_management.register", "Register"),
        ("project_management.collaboration", "Collaboration"),
        ("project_management.timesheets", "Timesheets"),
        ("project_management.dashboard", "Dashboard"),
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
        "project_management.risk",
        "project_management.portfolio",
        "project_management.register",
        "project_management.collaboration",
        "project_management.timesheets",
        "project_management.dashboard",
    ]
    assert context.navigationItems[0]["qmlSource"] == route_by_id["shell.home"].qml_path.as_uri()

    context.selectRoute("platform.admin")

    assert context.currentRouteId == "platform.admin"
    assert context.currentRouteSource == route_by_id["platform.admin"].qml_path.as_uri()

    context.selectRoute("platform.unknown")

    assert context.currentRouteId == "platform.admin"


def test_qml_login_view_model_keeps_empty_credentials_by_default() -> None:
    view_model = LoginViewModel()

    assert view_model.username == ""
    assert view_model.password == ""
    assert view_model.error_message == ""
    assert not view_model.is_busy


def test_qml_shell_does_not_replace_widget_entrypoint_yet() -> None:
    entrypoint = Path("main_qt.py").read_text(encoding="utf-8")

    assert "from src.ui.shell.app import main" in entrypoint
    assert "src.ui_qml.shell.app" not in entrypoint
