from src.ui_qml.modules.project_management.navigation import PM_CANONICAL_ROUTE_ID
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.ui_qml.shell.qml_registry import build_qml_route_registry


EXPECTED_COMPATIBILITY_PM_ROUTE_IDS = [
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
]


def test_project_management_qml_routes_point_to_workspace_files() -> None:
    routes = build_project_management_routes()

    assert [route.route_id for route in routes] == [
        PM_CANONICAL_ROUTE_ID,
        *EXPECTED_COMPATIBILITY_PM_ROUTE_IDS,
    ]
    assert all(route.module_code == "project_management" for route in routes)
    assert all(route.module_label == "Project Management" for route in routes)
    assert all(route.qml_path.exists() for route in routes)


def test_project_management_canonical_route_is_the_only_navigation_entry() -> None:
    """R2.7/R2.8: the shell exposes exactly ONE Project Management
    destination. The ten compatibility route ids remain registered/loadable (for
    deep-link compatibility) but are no longer separate drawer entries."""
    registry = build_qml_route_registry()
    route_ids = [route.route_id for route in registry.list_navigation_routes()]

    assert PM_CANONICAL_ROUTE_ID in route_ids
    for route_id in EXPECTED_COMPATIBILITY_PM_ROUTE_IDS:
        assert route_id not in route_ids


def test_project_management_compatibility_routes_remain_registered_for_deep_links() -> None:
    registry = build_qml_route_registry()
    all_route_ids = [route.route_id for route in registry.list_routes()]

    for route_id in EXPECTED_COMPATIBILITY_PM_ROUTE_IDS:
        assert route_id in all_route_ids

