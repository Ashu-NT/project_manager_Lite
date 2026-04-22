from pathlib import Path

import pytest

from src.ui_qml.shell.login import LoginViewModel
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.qml_registry import QmlRouteRegistry, build_qml_route_registry
from src.ui_qml.shell.routes import build_shell_routes


def test_qml_shell_routes_point_to_existing_qml_files() -> None:
    routes = build_shell_routes()

    assert [route.route_id for route in routes] == ["shell.main"]
    assert routes[0].qml_path.name == "MainWindow.qml"
    assert routes[0].qml_path.exists()


def test_qml_route_registry_rejects_duplicate_routes() -> None:
    route = build_shell_routes()[0]
    registry = QmlRouteRegistry([route])

    with pytest.raises(ValueError, match="already registered"):
        registry.register(route)


def test_qml_shell_navigation_view_models_are_built_from_registry() -> None:
    registry = build_qml_route_registry()
    items = build_main_window_navigation(registry)

    assert [(item.route_id, item.title) for item in items] == [
        ("shell.main", "Main Window")
    ]


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
