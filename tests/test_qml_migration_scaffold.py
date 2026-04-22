from pathlib import Path

from src.ui_qml.shell.login import LoginViewModel
from src.ui_qml.shell.main_window import build_main_window_navigation
from src.ui_qml.shell.navigation import build_navigation_items
from src.ui_qml.shell.qml_registry import QmlRouteRegistry, build_qml_route_registry
from src.ui_qml.shell.routes import QmlRoute, build_shell_routes


def test_qml_shell_registry_exposes_main_route():
    registry = build_qml_route_registry()
    route = registry.get("shell.app")

    assert route.title == "TECHASH Enterprise"
    assert route.qml_path.name == "App.qml"
    assert route.qml_path.exists()


def test_qml_shell_registry_rejects_duplicate_routes(tmp_path: Path):
    route = QmlRoute(
        route_id="duplicate",
        module_code="shell",
        module_label="Shell",
        group_label="Runtime",
        title="Duplicate",
        qml_path=tmp_path / "Duplicate.qml",
    )
    registry = QmlRouteRegistry([route])

    try:
        registry.register(route)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("Expected duplicate QML route registration to fail")


def test_qml_shell_navigation_view_models_are_route_shaped():
    items = build_navigation_items(build_shell_routes())

    assert len(items) == 2
    assert items[1].route_id == "shell.home"
    assert items[0].module_label == "Shell"
    assert items[0].group_label == "Runtime"


def test_qml_main_window_navigation_uses_registry_routes():
    navigation = build_main_window_navigation(build_qml_route_registry())

    assert [item.title for item in navigation] == ["QML Home"]


def test_qml_login_view_model_is_display_only():
    view_model = LoginViewModel()

    assert view_model.title == "Sign in"
    assert view_model.username_label == "Username"
    assert view_model.password_label == "Password"
    assert view_model.submit_label == "Continue"
