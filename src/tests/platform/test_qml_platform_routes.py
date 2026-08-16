from src.ui_qml.platform.routes import build_platform_routes
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def test_platform_qml_routes_point_to_workspace_files() -> None:
    # R5.9: the 4 legacy per-surface routes were retired once every
    # capability they hosted (or could be reached from) had its own
    # standalone extraction and no longer depended on
    # `platformCatalog.workspace("platform.<x>")` for header text.
    # `platform.workspace` is now the only registered Platform route.
    routes = build_platform_routes()

    assert [route.route_id for route in routes] == [
        "platform.workspace",
    ]
    assert all(route.qml_path.exists() for route in routes)


def test_platform_qml_routes_are_registered_for_navigation() -> None:
    registry = build_qml_route_registry()
    route_ids = [route.route_id for route in registry.list_navigation_routes()]

    assert "platform.workspace" in route_ids
