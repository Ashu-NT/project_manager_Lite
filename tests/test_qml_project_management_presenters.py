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
    build_project_management_financials_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.domain.enums import CostType, ProjectStatus, TaskStatus, WorkerType
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


def test_project_management_workspace_catalog_exposes_typed_projects_controller() -> None:
    projects_api = build_project_management_projects_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(
                    id="proj-1",
                    name="Plant Upgrade",
                    description="Replace switchgear and commission the new line.",
                    status=ProjectStatus.ACTIVE,
                    start_date=date(2026, 5, 1),
                    end_date=date(2026, 8, 15),
                    client_name="Contoso Manufacturing",
                    client_contact="alex@contoso.example",
                    planned_budget=250000.0,
                    currency="EUR",
                    version=4,
                ),
                SimpleNamespace(
                    id="proj-2",
                    name="Warehouse Retrofit",
                    description="Upgrade lighting and controls.",
                    status=ProjectStatus.ON_HOLD,
                    start_date=None,
                    end_date=None,
                    client_name="Northwind Logistics",
                    client_contact="jamie@northwind.example",
                    planned_budget=None,
                    currency=None,
                    version=2,
                ),
            ]
        )
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_projects=projects_api)
    )

    controller = catalog.projectsWorkspace

    assert controller.workspace["routeId"] == "project_management.projects"
    assert controller.overview["title"] == "Projects"
    assert controller.overview["metrics"][0]["value"] == "2"
    assert controller.projects["items"][0]["title"] == "Plant Upgrade"
    assert controller.selectedProject["title"] == "Plant Upgrade"

    controller.setStatusFilter("ON_HOLD")

    assert controller.selectedStatusFilter == "ON_HOLD"
    assert controller.projects["items"][0]["title"] == "Warehouse Retrofit"

    controller.setSearchText("plant")

    assert controller.projects["items"] == []
    assert controller.emptyState == "No projects match the current filters."


def test_project_management_workspace_catalog_exposes_typed_financials_controller() -> None:
    financials_api = build_project_management_financials_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(
                    id="proj-1",
                    name="Plant Upgrade",
                    planned_budget=5000.0,
                    currency="EUR",
                ),
                SimpleNamespace(
                    id="proj-2",
                    name="Warehouse Retrofit",
                    planned_budget=3200.0,
                    currency="USD",
                ),
            ]
        ),
        task_service=_FakeTaskOptionService(
            {
                "proj-1": [
                    SimpleNamespace(id="task-1", name="Cable Pull", start_date=date(2026, 5, 3)),
                ],
                "proj-2": [],
            }
        ),
        cost_service=_FakeFinancialCostService(
            {
                "proj-1": [
                    _build_cost_record(
                        cost_id="cost-1",
                        project_id="proj-1",
                        task_id="task-1",
                        description="Electrical material package",
                        planned_amount=1500.0,
                        committed_amount=900.0,
                        actual_amount=450.0,
                        cost_type=CostType.MATERIAL,
                        incurred_date=date(2026, 5, 4),
                        currency_code="EUR",
                        version=2,
                    ),
                    _build_cost_record(
                        cost_id="cost-2",
                        project_id="proj-1",
                        task_id=None,
                        description="Scaffold labor support",
                        planned_amount=800.0,
                        committed_amount=500.0,
                        actual_amount=200.0,
                        cost_type=CostType.LABOR,
                        incurred_date=date(2026, 5, 5),
                        currency_code="EUR",
                        version=1,
                    ),
                ],
                "proj-2": [],
            }
        ),
        finance_service=_FakeFinanceDesktopService(
            {
                "proj-1": SimpleNamespace(
                    project_currency="EUR",
                    budget=5000.0,
                    planned=2300.0,
                    committed=1400.0,
                    actual=650.0,
                    exposure=1400.0,
                    available=3600.0,
                    ledger=[
                        SimpleNamespace(
                            source_label="Direct Cost",
                            stage="actual",
                            amount=450.0,
                            currency="EUR",
                            reference_label="Electrical material package",
                            task_name="Cable Pull",
                            resource_name=None,
                            occurred_on=date(2026, 5, 4),
                            included_in_policy=True,
                        )
                    ],
                    cashflow=[
                        SimpleNamespace(
                            period_key="2026-05",
                            planned=2300.0,
                            committed=1400.0,
                            actual=650.0,
                            forecast=2300.0,
                            exposure=1400.0,
                        )
                    ],
                    by_source=[
                        SimpleNamespace(
                            dimension="source",
                            key="direct_cost",
                            label="Direct Cost",
                            planned=2300.0,
                            committed=1400.0,
                            actual=650.0,
                            forecast=2300.0,
                            exposure=1400.0,
                        )
                    ],
                    by_cost_type=[
                        SimpleNamespace(
                            dimension="cost_type",
                            key="MATERIAL",
                            label="Material",
                            planned=1500.0,
                            committed=900.0,
                            actual=450.0,
                            forecast=1500.0,
                            exposure=900.0,
                        )
                    ],
                    by_resource=[],
                    by_task=[],
                    notes=["Finance snapshot preview generated from PM financial services."],
                ),
                "proj-2": SimpleNamespace(
                    project_currency="USD",
                    budget=3200.0,
                    planned=0.0,
                    committed=0.0,
                    actual=0.0,
                    exposure=0.0,
                    available=3200.0,
                    ledger=[],
                    cashflow=[],
                    by_source=[],
                    by_cost_type=[],
                    by_resource=[],
                    by_task=[],
                    notes=[],
                ),
            }
        ),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_financials=financials_api)
    )

    controller = catalog.financialsWorkspace

    assert controller.workspace["routeId"] == "project_management.financials"
    assert controller.overview["title"] == "Financials"
    assert controller.projectOptions[0]["label"] == "Plant Upgrade"
    assert controller.costTypeOptions[1]["value"] == "LABOR"
    assert controller.costs["items"][0]["title"] == "Electrical material package"
    assert controller.selectedCost["title"] == "Electrical material package"
    assert controller.cashflow["items"][0]["title"] == "2026-05"

    controller.setCostTypeFilter("LABOR")

    assert controller.selectedCostType == "LABOR"
    assert [item["title"] for item in controller.costs["items"]] == ["Scaffold labor support"]

    controller.setSearchText("cable")

    assert controller.costs["items"] == []
    assert controller.emptyState == "No cost items match the current filters."


def test_project_management_workspace_catalog_exposes_typed_resources_controller() -> None:
    resources_api = build_project_management_resources_desktop_api(
        resource_service=_FakeResourceService(
            [
                SimpleNamespace(
                    id="res-1",
                    name="Electrical Crew",
                    role="Lead Technician",
                    hourly_rate=95.0,
                    is_active=True,
                    cost_type=CostType.LABOR,
                    currency_code="EUR",
                    version=3,
                    capacity_percent=110.0,
                    address="Site Office",
                    contact="crew@example.com",
                    worker_type=WorkerType.EXTERNAL,
                    employee_id=None,
                ),
                SimpleNamespace(
                    id="res-2",
                    name="Alex Taylor",
                    role="Planner",
                    hourly_rate=80.0,
                    is_active=False,
                    cost_type=CostType.LABOR,
                    currency_code="USD",
                    version=2,
                    capacity_percent=100.0,
                    address="",
                    contact="alex@example.com",
                    worker_type=WorkerType.EMPLOYEE,
                    employee_id="emp-1",
                ),
            ]
        ),
        employee_service=_FakeEmployeeService(),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_resources=resources_api)
    )

    controller = catalog.resourcesWorkspace

    assert controller.workspace["routeId"] == "project_management.resources"
    assert controller.overview["title"] == "Resources"
    assert controller.categoryOptions[1]["value"] == "LABOR"
    assert controller.employeeOptions[0]["context"] == "Operations | Plant North"
    assert controller.resources["items"][0]["title"] == "Electrical Crew"
    assert controller.selectedResource["title"] == "Electrical Crew"

    controller.setActiveFilter("inactive")

    assert controller.selectedActiveFilter == "inactive"
    assert [item["title"] for item in controller.resources["items"]] == ["Alex Taylor"]

    controller.setSearchText("crew")

    assert controller.resources["items"] == []
    assert controller.emptyState == "No resources match the current filters."


def test_project_management_workspace_catalog_exposes_typed_risk_and_register_controller() -> None:
    register_api = build_project_management_register_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        register_service=_FakeRegisterService(
            [
                _build_register_record(
                    entry_id="reg-1",
                    project_id="proj-1",
                    entry_type=RegisterEntryType.RISK,
                    title="Critical supplier dependency",
                    description="Switchgear release note is still pending.",
                    severity=RegisterEntrySeverity.CRITICAL,
                    status=RegisterEntryStatus.OPEN,
                    owner_name="Lead Planner",
                    due_date=date(2026, 5, 2),
                    impact_summary="Commissioning could slip by one week.",
                    response_plan="Escalate with vendor and approve alternates.",
                    version=2,
                ),
                _build_register_record(
                    entry_id="reg-2",
                    project_id="proj-1",
                    entry_type=RegisterEntryType.CHANGE,
                    title="Additional cable tray scope",
                    description="New field route requires material and labor change.",
                    severity=RegisterEntrySeverity.MEDIUM,
                    status=RegisterEntryStatus.IN_PROGRESS,
                    owner_name="Project Engineer",
                    due_date=date(2026, 5, 7),
                    impact_summary="Budget exposure needs approval.",
                    response_plan="Issue estimate and submit change control.",
                    version=1,
                ),
                _build_register_record(
                    entry_id="reg-3",
                    project_id="proj-2",
                    entry_type=RegisterEntryType.ISSUE,
                    title="Permit handoff blocked",
                    description="Permit package is still pending city review.",
                    severity=RegisterEntrySeverity.HIGH,
                    status=RegisterEntryStatus.IN_PROGRESS,
                    owner_name="PM",
                    due_date=date(2026, 5, 6),
                    impact_summary="Mobilization is at risk.",
                    response_plan="Daily escalation with local authority.",
                    version=1,
                ),
            ]
        ),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            project_management_risk=register_api,
            project_management_register=register_api,
        )
    )

    risk_controller = catalog.riskWorkspace
    register_controller = catalog.registerWorkspace

    assert risk_controller.workspace["routeId"] == "project_management.risk"
    assert risk_controller.overview["title"] == "Risk"
    assert risk_controller.entries["items"][0]["title"] == "Critical supplier dependency"
    assert risk_controller.selectedEntry["title"] == "Critical supplier dependency"
    assert risk_controller.urgentEntries["items"][0]["title"] == "Critical supplier dependency"

    risk_controller.setSeverityFilter("HIGH")

    assert [item["title"] for item in risk_controller.entries["items"]] == []
    assert risk_controller.emptyState == "No risks match the current filters."

    assert register_controller.workspace["routeId"] == "project_management.register"
    assert register_controller.typeOptions[1]["value"] == "RISK"
    assert register_controller.entries["items"][0]["title"] == "Critical supplier dependency"
    assert register_controller.selectedEntry["fields"][2]["label"] == "Impact"

    register_controller.setTypeFilter("CHANGE")

    assert [item["title"] for item in register_controller.entries["items"]] == [
        "Additional cable tray scope"
    ]


def test_project_management_workspace_catalog_exposes_typed_tasks_controller() -> None:
    tasks_api = build_project_management_tasks_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        task_service=_FakeTaskService(
            [
                _build_task_record(
                    task_id="task-1",
                    project_id="proj-1",
                    name="Cable Pull",
                    description="Primary feeder cable installation.",
                    status=TaskStatus.IN_PROGRESS,
                    start_date=date(2026, 5, 3),
                    end_date=date(2026, 5, 6),
                    duration_days=4,
                    priority=70,
                    percent_complete=45.0,
                    deadline=date(2026, 5, 7),
                ),
                _build_task_record(
                    task_id="task-2",
                    project_id="proj-1",
                    name="Punchlist Closeout",
                    description="Commissioning closeout walkdown.",
                    status=TaskStatus.BLOCKED,
                    start_date=date(2026, 5, 8),
                    end_date=date(2026, 5, 9),
                    duration_days=2,
                    priority=95,
                    percent_complete=0.0,
                    deadline=date(2026, 5, 9),
                ),
                _build_task_record(
                    task_id="task-3",
                    project_id="proj-2",
                    name="Lighting Retrofit",
                    description="Warehouse fixture replacement.",
                    status=TaskStatus.TODO,
                    start_date=date(2026, 5, 10),
                    end_date=date(2026, 5, 12),
                    duration_days=3,
                    priority=40,
                    percent_complete=0.0,
                    deadline=date(2026, 5, 13),
                ),
            ]
        ),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_tasks=tasks_api)
    )

    controller = catalog.tasksWorkspace

    assert controller.workspace["routeId"] == "project_management.tasks"
    assert controller.overview["title"] == "Tasks"
    assert controller.projectOptions[0]["label"] == "Plant Upgrade"
    assert controller.selectedProjectId == "proj-1"
    assert controller.tasks["items"][0]["title"] == "Cable Pull"
    assert controller.selectedTask["title"] == "Cable Pull"

    controller.setStatusFilter("BLOCKED")

    assert controller.selectedStatusFilter == "BLOCKED"
    assert [item["title"] for item in controller.tasks["items"]] == ["Punchlist Closeout"]

    controller.setSearchText("cable")

    assert controller.tasks["items"] == []
    assert controller.emptyState == "No tasks match the current filters."


def test_project_management_workspace_catalog_exposes_typed_scheduling_controller() -> None:
    scheduling_api = build_project_management_scheduling_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit"),
            ]
        ),
        task_service=SimpleNamespace(
            list_tasks_for_project=lambda project_id: []
        ),
        scheduling_engine=_FakeSchedulingEngine(
            {
                "proj-1": [
                    _build_schedule_record(
                        task_id="task-1",
                        project_id="proj-1",
                        name="Cable Pull",
                        status=TaskStatus.IN_PROGRESS,
                        start_date=date(2026, 5, 3),
                        finish_date=date(2026, 5, 6),
                        latest_start=date(2026, 5, 3),
                        latest_finish=date(2026, 5, 6),
                        total_float_days=0,
                        is_critical=True,
                        deadline=date(2026, 5, 7),
                        late_by_days=0,
                        percent_complete=45.0,
                    ),
                    _build_schedule_record(
                        task_id="task-2",
                        project_id="proj-1",
                        name="Punchlist Closeout",
                        status=TaskStatus.BLOCKED,
                        start_date=date(2026, 5, 8),
                        finish_date=date(2026, 5, 9),
                        latest_start=date(2026, 5, 10),
                        latest_finish=date(2026, 5, 11),
                        total_float_days=2,
                        is_critical=False,
                        deadline=date(2026, 5, 9),
                        late_by_days=1,
                        percent_complete=0.0,
                    ),
                ],
                "proj-2": [],
            }
        ),
        work_calendar_service=_FakeWorkCalendarService(),
        work_calendar_engine=_FakeWorkCalendarEngine(),
        baseline_service=_FakeBaselineService(
            {
                "proj-1": [
                    SimpleNamespace(
                        id="base-2",
                        name="Weekly Freeze",
                        created_at=date(2026, 5, 7),
                    ),
                    SimpleNamespace(
                        id="base-1",
                        name="Original Plan",
                        created_at=date(2026, 5, 1),
                    ),
                ]
            }
        ),
        reporting_service=_FakeReportingService(
            {
                ("proj-1", "base-1", "base-2", False): [
                    SimpleNamespace(
                        task_id="task-1",
                        task_name="Cable Pull",
                        change_type="CHANGED",
                        baseline_a_start=date(2026, 5, 2),
                        baseline_a_finish=date(2026, 5, 5),
                        baseline_b_start=date(2026, 5, 3),
                        baseline_b_finish=date(2026, 5, 6),
                        start_shift_days=1,
                        finish_shift_days=1,
                        duration_delta_days=0,
                        planned_cost_delta=1200.0,
                    )
                ]
            }
        ),
    )
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(project_management_scheduling=scheduling_api)
    )

    controller = catalog.schedulingWorkspace

    assert controller.workspace["routeId"] == "project_management.scheduling"
    assert controller.overview["title"] == "Scheduling"
    assert controller.projectOptions[0]["label"] == "Plant Upgrade"
    assert controller.calendar["workingDays"][0]["checked"] is True
    assert controller.schedule["items"][0]["title"] == "Cable Pull"
    assert controller.criticalPath["items"][0]["title"] == "Cable Pull"
    assert controller.baselines["rows"][0]["title"] == "Cable Pull"

    controller.selectProject("proj-2")

    assert controller.selectedProjectId == "proj-2"
    assert controller.schedule["items"] == []
    assert controller.schedule["emptyState"] == "No scheduled tasks are available for the selected project."


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
    assert "import ProjectManagement.Dialogs 1.0" in qml_text
    assert "import ProjectManagement.Widgets 1.0" in qml_text
    assert "property var pmCatalog" not in qml_text
    assert "QML CRUD projects slice active" in qml_text
    assert "QML financials operations slice active" in qml_text
    assert "QML CRUD resources slice active" in qml_text
    assert "QML risk register slice active" in qml_text
    assert "QML governance register slice active" in qml_text
    assert "QML scheduling operations slice active" in qml_text
    assert "QML CRUD tasks slice active" in qml_text
    assert "QML read-only dashboard slice active" in qml_text


class _FakeEmployeeService:
    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        employees = [
            SimpleNamespace(
                id="emp-1",
                employee_code="EMP-001",
                full_name="Alex Taylor",
                title="Planner",
                department="Operations",
                site_name="Plant North",
                email="alex@example.com",
                phone="555-0100",
                is_active=True,
            ),
            SimpleNamespace(
                id="emp-2",
                employee_code="EMP-002",
                full_name="Jordan Blake",
                title="Supervisor",
                department="Maintenance",
                site_name="Plant South",
                email="jordan@example.com",
                phone="555-0101",
                is_active=False,
            ),
        ]
        if active_only is None:
            return employees
        return [
            employee
            for employee in employees
            if bool(employee.is_active) == bool(active_only)
        ]


class _FakeResourceService:
    def __init__(self, resources: list[SimpleNamespace] | None = None) -> None:
        self._resources = {
            resource.id: resource
            for resource in (resources or [])
        }

    def list_resources(self) -> list[SimpleNamespace]:
        return list(self._resources.values())


class _FakeRegisterService:
    def __init__(self, entries: list[SimpleNamespace] | None = None) -> None:
        self._entries = {
            entry.id: entry
            for entry in (entries or [])
        }

    def list_entries(
        self,
        *,
        project_id: str | None = None,
        entry_type: RegisterEntryType | None = None,
        status: RegisterEntryStatus | None = None,
        severity: RegisterEntrySeverity | None = None,
    ) -> list[SimpleNamespace]:
        return [
            entry
            for entry in self._entries.values()
            if (project_id is None or entry.project_id == project_id)
            and (entry_type is None or entry.entry_type == entry_type)
            and (status is None or entry.status == status)
            and (severity is None or entry.severity == severity)
        ]


class _FakeTaskService:
    def __init__(self, tasks: list[SimpleNamespace] | None = None) -> None:
        self._tasks = {
            task.id: task
            for task in (tasks or [])
        }

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [
            task
            for task in self._tasks.values()
            if task.project_id == project_id
        ]


class _FakeTaskOptionService:
    def __init__(self, tasks_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._tasks_by_project = tasks_by_project

    def list_tasks_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._tasks_by_project.get(project_id, []))


class _FakeFinancialCostService:
    def __init__(self, costs_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._costs_by_project = costs_by_project

    def list_cost_items_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._costs_by_project.get(project_id, []))


class _FakeFinanceDesktopService:
    def __init__(self, snapshots_by_project: dict[str, SimpleNamespace]) -> None:
        self._snapshots_by_project = snapshots_by_project

    def get_finance_snapshot(self, project_id: str) -> SimpleNamespace:
        return self._snapshots_by_project[project_id]


def _build_task_record(
    *,
    task_id: str,
    project_id: str,
    name: str,
    description: str,
    status: TaskStatus,
    start_date: date | None,
    end_date: date | None,
    duration_days: int | None,
    priority: int,
    percent_complete: float,
    deadline: date | None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=task_id,
        project_id=project_id,
        name=name,
        description=description,
        status=status,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration_days,
        priority=priority,
        percent_complete=percent_complete,
        actual_start=None,
        actual_end=None,
        deadline=deadline,
        version=1,
    )


def _build_cost_record(
    *,
    cost_id: str,
    project_id: str,
    task_id: str | None,
    description: str,
    planned_amount: float,
    committed_amount: float,
    actual_amount: float,
    cost_type: CostType,
    incurred_date: date | None,
    currency_code: str | None,
    version: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=cost_id,
        project_id=project_id,
        task_id=task_id,
        description=description,
        planned_amount=planned_amount,
        committed_amount=committed_amount,
        actual_amount=actual_amount,
        cost_type=cost_type,
        incurred_date=incurred_date,
        currency_code=currency_code,
        version=version,
    )


def _build_register_record(
    *,
    entry_id: str,
    project_id: str,
    entry_type: RegisterEntryType,
    title: str,
    description: str,
    severity: RegisterEntrySeverity,
    status: RegisterEntryStatus,
    owner_name: str | None,
    due_date: date | None,
    impact_summary: str,
    response_plan: str,
    version: int,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=entry_id,
        project_id=project_id,
        entry_type=entry_type,
        title=title,
        description=description,
        severity=severity,
        status=status,
        owner_name=owner_name,
        due_date=due_date,
        impact_summary=impact_summary,
        response_plan=response_plan,
        version=version,
    )


class _FakeSchedulingEngine:
    def __init__(self, schedules: dict[str, list[SimpleNamespace]]) -> None:
        self._schedules = schedules

    def recalculate_project_schedule(
        self,
        project_id: str,
        *,
        persist: bool = True,
    ) -> dict[str, SimpleNamespace]:
        return {
            item.task.id: item
            for item in self._schedules.get(project_id, [])
        }


class _FakeWorkCalendarService:
    def get_calendar(self) -> SimpleNamespace:
        return SimpleNamespace(
            working_days={0, 1, 2, 3, 4},
            hours_per_day=8.0,
        )

    def list_holidays(self) -> list[SimpleNamespace]:
        return [
            SimpleNamespace(
                id="holiday-1",
                date=date(2026, 5, 1),
                name="Labor Day",
            )
        ]


class _FakeWorkCalendarEngine:
    def add_working_days(self, start_date: date, working_days: int) -> date:
        return date.fromordinal(start_date.toordinal() + working_days)

    def is_working_day(self, target_date: date) -> bool:
        return target_date.weekday() < 5


class _FakeBaselineService:
    def __init__(self, baselines_by_project: dict[str, list[SimpleNamespace]]) -> None:
        self._baselines_by_project = baselines_by_project

    def list_baselines(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._baselines_by_project.get(project_id, []))


class _FakeReportingService:
    def __init__(self, rows_by_key: dict[tuple[str, str, str, bool], list[SimpleNamespace]]) -> None:
        self._rows_by_key = rows_by_key

    def compare_baselines(
        self,
        *,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
        include_unchanged: bool = False,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            rows=list(
                self._rows_by_key.get(
                    (project_id, baseline_a_id, baseline_b_id, include_unchanged),
                    [],
                )
            )
        )


def _build_schedule_record(
    *,
    task_id: str,
    project_id: str,
    name: str,
    status: TaskStatus,
    start_date: date | None,
    finish_date: date | None,
    latest_start: date | None,
    latest_finish: date | None,
    total_float_days: int | None,
    is_critical: bool,
    deadline: date | None,
    late_by_days: int | None,
    percent_complete: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        task=SimpleNamespace(
            id=task_id,
            project_id=project_id,
            name=name,
            status=status,
            percent_complete=percent_complete,
        ),
        earliest_start=start_date,
        earliest_finish=finish_date,
        latest_start=latest_start,
        latest_finish=latest_finish,
        total_float_days=total_float_days,
        is_critical=is_critical,
        deadline=deadline,
        late_by_days=late_by_days,
    )
