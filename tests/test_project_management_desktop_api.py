from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_dashboard_desktop_api,
    build_project_management_workspace_desktop_api,
)


EXPECTED_PM_WORKSPACE_KEYS = [
    "projects",
    "tasks",
    "scheduling",
    "resources",
    "financials",
    "risk",
    "portfolio",
    "register",
    "collaboration",
    "timesheets",
    "dashboard",
]


def test_project_management_desktop_api_lists_workspace_descriptors() -> None:
    api = build_project_management_workspace_desktop_api()
    descriptors = api.list_workspaces()

    assert [descriptor.key for descriptor in descriptors] == EXPECTED_PM_WORKSPACE_KEYS
    assert descriptors[0].title == "Projects"
    assert descriptors[0].summary == (
        "Project lifecycle, ownership, status, and project list workflows."
    )


def test_project_management_desktop_api_gets_workspace_by_route_id() -> None:
    api = build_project_management_workspace_desktop_api()

    descriptor = api.get_workspace("project_management.dashboard")

    assert descriptor is not None
    assert descriptor.key == "dashboard"
    assert descriptor.title == "Dashboard"
    assert api.get_workspace("project_management.unknown") is None


def test_project_management_dashboard_desktop_api_builds_empty_overview() -> None:
    api = build_project_management_dashboard_desktop_api()

    overview = api.build_empty_overview()

    assert overview.title == "Dashboard"
    assert overview.subtitle == "Select a project to see schedule and cost health."
    assert [metric.label for metric in overview.metrics] == [
        "Tasks",
        "Progress",
        "In flight",
        "Blocked",
        "Critical",
        "Late",
        "Cost variance",
        "Spend vs plan",
    ]


def test_project_management_dashboard_desktop_api_maps_dashboard_kpis() -> None:
    api = build_project_management_dashboard_desktop_api()
    dashboard_data = SimpleNamespace(
        kpi=SimpleNamespace(
            name="Plant Upgrade",
            tasks_total=10,
            tasks_completed=4,
            tasks_in_progress=3,
            task_blocked=1,
            critical_tasks=2,
            late_tasks=1,
            cost_variance=-2500.5,
            total_actual_cost=9000.0,
            total_planned_cost=12000.0,
        )
    )

    overview = api.build_overview_from_dashboard_data(
        project_name="Plant Upgrade",
        dashboard_data=dashboard_data,
    )

    metric_by_label = {metric.label: metric for metric in overview.metrics}
    assert overview.title == "Plant Upgrade"
    assert metric_by_label["Tasks"].value == "4 / 10"
    assert metric_by_label["Progress"].value == "40.00%"
    assert metric_by_label["Cost variance"].value == "-2,500.50"
    assert metric_by_label["Spend vs plan"].value == "9,000 / 12,000"


def test_project_management_desktop_api_does_not_import_qml_or_infra() -> None:
    api_root = Path("src/core/modules/project_management/api/desktop")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in api_root.rglob("*.py")
        if "__pycache__" not in path.parts
    )

    assert "src.ui_qml" not in source_text
    assert "ui_qml" not in source_text
    assert "infrastructure.persistence" not in source_text
