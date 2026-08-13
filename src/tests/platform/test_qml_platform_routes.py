from src.ui_qml.platform.routes import build_platform_routes
from src.ui_qml.shell.qml_registry import build_qml_route_registry


def test_platform_qml_routes_point_to_workspace_files() -> None:
    routes = build_platform_routes()

    assert [route.route_id for route in routes] == [
        "platform.workspace",
        "platform.admin",
        "platform.control",
        "platform.settings",
        "platform.tenants",
    ]
    assert all(route.qml_path.exists() for route in routes)


def test_platform_qml_routes_are_registered_for_navigation() -> None:
    # R2: the 4 legacy per-surface routes are superseded by the single
    # unified "platform.workspace" entry -- they stay registered (for their
    # own internal workspace()/qml_path lookups and offscreen-load coverage)
    # but are intentionally excluded from the navigation drawer.
    registry = build_qml_route_registry()
    route_ids = [route.route_id for route in registry.list_navigation_routes()]

    assert "platform.workspace" in route_ids
    assert "platform.admin" not in route_ids
    assert "platform.control" not in route_ids
    assert "platform.settings" not in route_ids
    assert "platform.tenants" not in route_ids

