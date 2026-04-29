from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.ui_qml.modules.project_management.presenters import (
    ProjectDashboardPresenter,
    build_project_management_workspace_presenters,
)
from src.ui_qml.modules.project_management.routes import build_project_management_routes
from src.core.modules.project_management.api.desktop import (
    build_project_management_dashboard_desktop_api,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


def test_project_management_workspace_presenters_match_qml_routes() -> None:
    routes = build_project_management_routes()
    presenters = build_project_management_workspace_presenters()

    assert list(presenters) == [route.route_id for route in routes]

    for route in routes:
        view_model = presenters[route.route_id].build_view_model()
        assert view_model.route_id == route.route_id
        assert view_model.title == route.title
        assert view_model.summary
        assert view_model.migration_status == "QML landing zone ready"
        assert view_model.legacy_runtime_status == "Existing QWidget screen remains active"


def test_project_management_workspace_catalog_exposes_qml_safe_maps() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    workspace = catalog.workspace("project_management.projects")

    assert workspace == {
        "routeId": "project_management.projects",
        "title": "Projects",
        "summary": "Project lifecycle, ownership, status, and project list workflows.",
        "migrationStatus": "QML landing zone ready",
        "legacyRuntimeStatus": "Existing QWidget screen remains active",
    }


def test_project_management_workspace_catalog_exposes_typed_dashboard_controller() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    workspace = catalog.dashboardWorkspace.workspace
    overview = catalog.dashboardWorkspace.overview

    assert workspace["routeId"] == "project_management.dashboard"
    assert workspace["migrationStatus"] == "QML landing zone ready"
    assert overview["title"] == "Dashboard"
    assert overview["metrics"][0]["label"] == "Tasks"


def test_project_management_workspace_catalog_exposes_real_dashboard_snapshot_state() -> None:
    desktop_api = build_project_management_dashboard_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        baseline_service=SimpleNamespace(
            list_baselines=lambda project_id: [
                SimpleNamespace(
                    id=f"{project_id}-base-1",
                    name="Latest Freeze",
                    created_at=datetime(2026, 4, 27, 9, 0),
                )
            ]
        ),
        dashboard_service=SimpleNamespace(
            get_dashboard_data=lambda project_id, baseline_id=None: SimpleNamespace(
                kpi=SimpleNamespace(
                    project_id=project_id,
                    name="Plant Upgrade" if project_id == "proj-1" else "Warehouse Retrofit",
                    tasks_total=8,
                    tasks_completed=3,
                    tasks_in_progress=2,
                    task_blocked=1,
                    critical_tasks=1,
                    late_tasks=0,
                    cost_variance=1500.0,
                    total_actual_cost=5000.0,
                    total_planned_cost=6500.0,
                ),
                alerts=["Field issue requires review"],
                milestone_health=[],
                critical_watchlist=[],
                burndown=[
                    SimpleNamespace(day=date(2026, 4, 28), remaining_tasks=8),
                    SimpleNamespace(day=date(2026, 4, 29), remaining_tasks=5),
                ],
                resource_load=[],
                upcoming_tasks=[],
                evm=SimpleNamespace(
                    as_of=date(2026, 4, 29),
                    CPI=1.02,
                    SPI=0.98,
                    PV=5000.0,
                    EV=4900.0,
                    AC=4800.0,
                    EAC=6400.0,
                    VAC=100.0,
                    TCPI_to_BAC=0.99,
                    TCPI_to_EAC=1.01,
                    status_text="Cost is favorable. Schedule is near target. Forecast is stable. TCPI is manageable.",
                ),
                register_summary=SimpleNamespace(
                    open_risks=1,
                    open_issues=0,
                    pending_changes=1,
                    overdue_items=0,
                    critical_items=1,
                    urgent_items=[
                        SimpleNamespace(
                            entry_id="urgent-1",
                            entry_type=RegisterEntryType.RISK,
                            title="Field issue requires review",
                            severity=RegisterEntrySeverity.CRITICAL,
                            status=RegisterEntryStatus.OPEN,
                            owner_name="PM",
                            due_date=date(2026, 5, 1),
                        )
                    ],
                ),
                cost_sources=SimpleNamespace(
                    rows=[
                        SimpleNamespace(
                            source_label="Direct Cost",
                            planned=5000.0,
                            committed=4500.0,
                            actual=4800.0,
                        )
                    ]
                ),
            ),
            get_portfolio_data=lambda: SimpleNamespace(
                kpi=SimpleNamespace(
                    project_id="__portfolio__",
                    name="Portfolio Overview",
                    tasks_total=0,
                    tasks_completed=0,
                    tasks_in_progress=0,
                    task_blocked=0,
                    critical_tasks=0,
                    late_tasks=0,
                    cost_variance=0.0,
                    total_actual_cost=0.0,
                    total_planned_cost=0.0,
                ),
                portfolio=SimpleNamespace(projects_total=2, project_rankings=[]),
                alerts=[],
                milestone_health=[],
                critical_watchlist=[],
                burndown=[],
                resource_load=[],
                upcoming_tasks=[],
                evm=None,
                register_summary=None,
                cost_sources=None,
            ),
        ),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_dashboard=desktop_api)
    )

    controller = catalog.dashboardWorkspace

    assert controller.projectOptions[1]["label"] == "Plant Upgrade"
    assert controller.selectedProjectId == "proj-1"
    assert controller.baselineOptions[1]["value"] == "proj-1-base-1"
    assert controller.panels[0]["title"] == "Earned Value (EVM)"
    assert controller.charts[0]["chartType"] == "line"
    assert controller.sections[0]["title"] == "Alerts"

    controller.selectBaseline("proj-1-base-1")

    assert controller.selectedBaselineId == "proj-1-base-1"
    assert controller.panels[1]["rows"][0]["label"] == "Open risks"
    assert controller.sections[4]["title"] == "Urgent Register Items"


def test_project_management_workspace_catalog_returns_empty_unknown_workspace() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    workspace = catalog.workspace("project_management.unknown")

    assert workspace["routeId"] == "project_management.unknown"
    assert workspace["title"] == ""
    assert workspace["summary"] == ""


def test_project_dashboard_presenter_exposes_empty_overview_view_model() -> None:
    presenter = ProjectDashboardPresenter()

    overview = presenter.build_empty_overview()

    assert overview.title == "Dashboard"
    assert overview.metrics[0].label == "Tasks"
    assert overview.metrics[0].value == "0 / 0"
    assert len(overview.metrics) == 8


def test_project_management_workspace_catalog_exposes_dashboard_overview() -> None:
    catalog = ProjectManagementWorkspaceCatalog()

    overview = catalog.dashboardOverview()

    assert overview["title"] == "Dashboard"
    assert len(overview["metrics"]) == 8
    assert overview["metrics"][0] == {
        "label": "Tasks",
        "value": "0 / 0",
        "supportingText": "Done / Total",
    }


def test_project_management_qml_presenters_do_not_import_legacy_widget_or_infra() -> None:
    source_root = Path("src/ui_qml/modules/project_management")
    source_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.parts
    )

    assert "src.ui.modules.project_management" not in source_text
    assert "ui.modules.project_management" not in source_text
    assert "infrastructure.persistence" not in source_text
    assert "repositories" not in source_text


def test_project_management_qml_uses_named_modules_and_typed_catalog_properties() -> None:
    qml_root = Path("src/ui_qml/modules/project_management/qml")
    qml_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in qml_root.rglob("*.qml")
        if "__pycache__" not in path.parts
    )

    assert "import ProjectManagement.Controllers 1.0" in qml_text
    assert "import ProjectManagement.Widgets 1.0" in qml_text
    assert "property var pmCatalog" not in qml_text
    assert "QML read-only dashboard slice active" in qml_text
