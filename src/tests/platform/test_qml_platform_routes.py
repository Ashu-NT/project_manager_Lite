from src.ui_qml.platform.routes import build_platform_routes
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def test_platform_qml_routes_point_to_workspace_files() -> None:
    # `platform.workspace` is the only registered Platform route now that every
    # capability has its own standalone extraction.
    routes = build_platform_routes()

    assert [route.route_id for route in routes] == [
        "platform.workspace",
    ]
    assert all(route.qml_path.exists() for route in routes)


def test_platform_qml_routes_are_registered_for_navigation() -> None:
    registry = build_qml_route_registry()
    route_ids = [route.route_id for route in registry.list_navigation_routes()]

    assert "platform.workspace" in route_ids
