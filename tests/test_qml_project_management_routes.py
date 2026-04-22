from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.shell.qml_registry import build_qml_route_registry


EXPECTED_PM_ROUTE_IDS = [
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


def test_project_management_qml_routes_point_to_workspace_files() -> None:
    routes = build_project_management_routes()

    assert [route.route_id for route in routes] == EXPECTED_PM_ROUTE_IDS
    assert all(route.module_code == "project_management" for route in routes)
    assert all(route.module_label == "Project Management" for route in routes)
    assert all(route.qml_path.exists() for route in routes)


def test_project_management_qml_routes_are_registered_for_navigation() -> None:
    registry = build_qml_route_registry()
    route_ids = [route.route_id for route in registry.list_navigation_routes()]

    for route_id in EXPECTED_PM_ROUTE_IDS:
        assert route_id in route_ids
