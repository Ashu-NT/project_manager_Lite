from src.ui_qml.modules.maintenance.routes import build_maintenance_routes
from src.ui_qml.shell.qml_registry import build_qml_route_registry


EXPECTED_ROUTE_IDS = [
    "maintenance_management.dashboard",
    "maintenance_management.assets",
    "maintenance_management.work_requests",
    "maintenance_management.work_orders",
    "maintenance_management.preventive",
    "maintenance_management.reliability",
    "maintenance_management.planner",
]


def test_maintenance_qml_routes_point_to_workspace_files() -> None:
    routes = build_maintenance_routes()

    assert [route.route_id for route in routes] == EXPECTED_ROUTE_IDS
    assert all(route.module_code == "maintenance" for route in routes)
    assert all(route.qml_path.exists() for route in routes)


def test_maintenance_qml_routes_are_registered_for_navigation() -> None:
    registry = build_qml_route_registry()

    assert [
        route.route_id
        for route in registry.list_navigation_routes()
        if route.module_code == "maintenance"
    ] == EXPECTED_ROUTE_IDS
