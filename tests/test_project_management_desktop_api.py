from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_portfolio_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
    build_project_management_timesheets_desktop_api,
    build_project_management_workspace_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    DependencyType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    PortfolioProjectDependency,
    PortfolioProjectDependencyView,
    PortfolioRecentAction,
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
    PortfolioScoringTemplate,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.core.platform.time.application import TimesheetReviewDetail
from src.core.platform.time.domain import TimeEntry, TimesheetPeriod, TimesheetPeriodStatus


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


def test_project_management_collaboration_desktop_api_builds_snapshot_and_marks_mentions_read() -> None:
    service = _FakeCollaborationService()
    api = build_project_management_collaboration_desktop_api(
        collaboration_service=service
    )

    snapshot = api.build_snapshot(limit=50)

    assert snapshot.notifications[0].notification_type_label == "Approval"
    assert snapshot.notifications[0].created_at_label == "2026-05-01 09:30"
    assert snapshot.inbox[0].mentions_label == "@planner"
    assert snapshot.recent_activity[0].unread is False
    assert snapshot.active_presence[0].who_label == "Alex Taylor (@planner)"
    assert snapshot.active_presence[0].activity_label == "Reviewing"

    api.mark_task_mentions_read("task-1")

    assert service.marked_task_ids == ["task-1"]


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


def test_project_management_dashboard_desktop_api_builds_preview_snapshot() -> None:
    api = build_project_management_dashboard_desktop_api()

    snapshot = api.build_snapshot()

    assert snapshot.selected_project_id == "__portfolio__"
    assert snapshot.project_options[0].label == "Portfolio Overview"
    assert snapshot.baseline_options[0].label == "Portfolio view"
    assert snapshot.panels[0].title == "Earned Value (EVM)"
    assert snapshot.charts[0].title == "Burndown / Status Rollup"
    assert snapshot.sections[0].title == "Dashboard Preview"
    assert "not connected" in snapshot.empty_state


def test_project_management_dashboard_desktop_api_builds_service_snapshot() -> None:
    api = build_project_management_dashboard_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [SimpleNamespace(id="proj-1", name="Plant Upgrade")]
        ),
        baseline_service=SimpleNamespace(
            list_baselines=lambda _project_id: [
                SimpleNamespace(
                    id="base-1",
                    name="Weekly Freeze",
                    created_at=datetime(2026, 4, 27, 10, 30),
                )
            ]
        ),
        dashboard_service=SimpleNamespace(
            get_dashboard_data=lambda project_id, baseline_id=None: SimpleNamespace(
                kpi=SimpleNamespace(
                    project_id=project_id,
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
                ),
                alerts=["Owner assignment missing on punchlist"],
                milestone_health=[
                    SimpleNamespace(
                        task_id="mile-1",
                        task_name="Mechanical Completion",
                        status_label="Watch",
                        owner_name="Alex",
                        target_date=None,
                        slip_days=3,
                    )
                ],
                critical_watchlist=[
                    SimpleNamespace(
                        task_id="crit-1",
                        task_name="Cable Pull",
                        status_label="Critical",
                        owner_name="Jordan",
                        finish_date=None,
                        total_float_days=0,
                        late_by_days=2,
                    )
                ],
                resource_load=[
                    SimpleNamespace(
                        resource_id="res-1",
                        resource_name="Electrical Crew",
                        utilization_percent=112.0,
                        total_allocation_percent=112.0,
                        capacity_percent=100.0,
                        tasks_count=5,
                    )
                ],
                upcoming_tasks=[
                    SimpleNamespace(
                        task_id="task-1",
                        name="Commissioning Pack",
                        is_late=False,
                        is_critical=True,
                        start_date=date(2026, 4, 30),
                        end_date=date(2026, 5, 4),
                        main_resource="Taylor",
                        percent_complete=55.0,
                    )
                ],
                burndown=[
                    SimpleNamespace(day=date(2026, 4, 28), remaining_tasks=8),
                    SimpleNamespace(day=date(2026, 4, 29), remaining_tasks=6),
                    SimpleNamespace(day=date(2026, 4, 30), remaining_tasks=5),
                ],
                evm=SimpleNamespace(
                    as_of=date(2026, 4, 30),
                    CPI=0.92,
                    SPI=0.88,
                    PV=12000.0,
                    EV=10400.0,
                    AC=11300.0,
                    EAC=13200.0,
                    VAC=-1200.0,
                    TCPI_to_BAC=1.11,
                    TCPI_to_EAC=1.03,
                    status_text="Cost is unfavorable. Schedule is behind target. Forecast is trending over budget. TCPI needs recovery focus.",
                ),
                register_summary=SimpleNamespace(
                    open_risks=3,
                    open_issues=2,
                    pending_changes=1,
                    overdue_items=1,
                    critical_items=2,
                    urgent_items=[
                        SimpleNamespace(
                            entry_id="reg-1",
                            entry_type=RegisterEntryType.RISK,
                            title="Critical supplier dependency",
                            severity=RegisterEntrySeverity.CRITICAL,
                            status=RegisterEntryStatus.OPEN,
                            owner_name="Lead Planner",
                            due_date=date(2026, 5, 2),
                        )
                    ],
                ),
                cost_sources=SimpleNamespace(
                    rows=[
                        SimpleNamespace(
                            source_label="Direct Cost",
                            planned=7000.0,
                            committed=6500.0,
                            actual=7200.0,
                        ),
                        SimpleNamespace(
                            source_label="Computed Labor",
                            planned=5000.0,
                            committed=0.0,
                            actual=4100.0,
                        ),
                    ]
                ),
            )
        ),
    )

    snapshot = api.build_snapshot(project_id="proj-1", baseline_id="base-1")

    assert snapshot.selected_project_id == "proj-1"
    assert snapshot.selected_baseline_id == "base-1"
    assert snapshot.baseline_options[1].label == "Weekly Freeze (2026-04-27 10:30)"
    assert snapshot.overview.title == "Plant Upgrade"
    assert [panel.title for panel in snapshot.panels] == [
        "Earned Value (EVM)",
        "Register Summary",
        "Cost Sources",
    ]
    assert snapshot.panels[0].hint == "As of 2026-04-30 (baseline: Weekly Freeze (2026-04-27 10:30))"
    assert snapshot.panels[0].metrics[0].label == "CPI"
    assert snapshot.panels[1].rows[3].tone == "danger"
    assert snapshot.panels[2].rows[0].supporting_text == "Committed: 6,500"
    assert [chart.title for chart in snapshot.charts] == ["Burndown", "Resource Load"]
    assert snapshot.charts[0].chart_type == "line"
    assert snapshot.charts[0].points[0].target_value == 8.0
    assert snapshot.charts[1].points[0].tone == "danger"
    assert [section.title for section in snapshot.sections] == [
        "Alerts",
        "Milestones",
        "Critical Path",
        "Upcoming Work",
        "Urgent Register Items",
    ]
    assert snapshot.sections[0].items[0].title == "Owner assignment missing on punchlist"
    assert snapshot.sections[2].items[0].meta_text == "Late by 2 day(s)"
    assert snapshot.sections[3].items[0].meta_text == "Progress: 55.00%"
    assert snapshot.sections[4].items[0].status_label == "Critical"


def test_project_management_projects_desktop_api_lists_statuses() -> None:
    api = build_project_management_projects_desktop_api()

    statuses = api.list_statuses()

    assert [status.value for status in statuses] == [
        "PLANNED",
        "ACTIVE",
        "ON_HOLD",
        "COMPLETED",
    ]
    assert statuses[2].label == "On Hold"


def test_project_management_projects_desktop_api_mutates_project_records() -> None:
    service = _FakeProjectService()
    api = build_project_management_projects_desktop_api(project_service=service)

    created = api.create_project(
        SimpleNamespace(
            name="Plant Upgrade",
            description="Replace switchgear and commission the new line.",
            status="ACTIVE",
            client_name="Contoso Manufacturing",
            client_contact="alex@contoso.example",
            planned_budget=250000.0,
            currency="eur",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 8, 15),
        )
    )

    listed = api.list_projects()

    assert created.status == "ACTIVE"
    assert listed[0].planned_budget_label == "EUR 250,000.00"
    assert listed[0].status_label == "Active"

    updated = api.update_project(
        SimpleNamespace(
            project_id=created.id,
            expected_version=service.get_project(created.id).version,
            name="Plant Upgrade Phase 1",
            description="Updated execution scope.",
            status="ON_HOLD",
            client_name="Contoso Manufacturing",
            client_contact="jamie@contoso.example",
            planned_budget=275000.0,
            currency="usd",
            start_date=date(2026, 5, 10),
            end_date=date(2026, 8, 20),
        )
    )

    assert updated.name == "Plant Upgrade Phase 1"
    assert updated.status == "ON_HOLD"
    assert updated.planned_budget_label == "USD 275,000.00"

    completed = api.set_project_status(created.id, "COMPLETED")

    assert completed.status == "COMPLETED"
    assert completed.status_label == "Completed"

    api.delete_project(created.id)

    assert api.list_projects() == ()


def test_project_management_resources_desktop_api_mutates_resource_records() -> None:
    resource_service = _FakeResourceService()
    employee_service = _FakeEmployeeService()
    api = build_project_management_resources_desktop_api(
        resource_service=resource_service,
        employee_service=employee_service,
    )

    worker_types = api.list_worker_types()
    categories = api.list_categories()
    employee_options = api.list_employees()

    assert [option.value for option in worker_types] == ["EMPLOYEE", "EXTERNAL"]
    assert categories[0].value == "LABOR"
    assert employee_options[0].context == "Operations | Plant North"

    created = api.create_resource(
        SimpleNamespace(
            name="Electrical Crew",
            role="Lead Technician",
            hourly_rate=95.0,
            is_active=True,
            cost_type="LABOR",
            currency_code="eur",
            capacity_percent=110.0,
            address="Site Office",
            contact="crew@example.com",
            worker_type="EXTERNAL",
            employee_id=None,
        )
    )

    listed = api.list_resources()

    assert created.worker_type == "EXTERNAL"
    assert listed[0].hourly_rate_label == "EUR 95.00"
    assert listed[0].capacity_label == "110.0%"

    employee_resource = api.create_resource(
        SimpleNamespace(
            name="",
            role="",
            hourly_rate=80.0,
            is_active=True,
            cost_type="LABOR",
            currency_code="usd",
            capacity_percent=100.0,
            address="",
            contact="",
            worker_type="EMPLOYEE",
            employee_id="emp-1",
        )
    )

    assert employee_resource.name == "Alex Taylor"
    assert employee_resource.employee_context == "Operations | Plant North"

    updated = api.update_resource(
        SimpleNamespace(
            resource_id=created.id,
            expected_version=resource_service.get_resource(created.id).version,
            name="Electrical Crew A",
            role="Field Supervisor",
            hourly_rate=105.0,
            is_active=True,
            cost_type="EQUIPMENT",
            currency_code="usd",
            capacity_percent=125.0,
            address="Warehouse Annex",
            contact="supervisor@example.com",
            worker_type="EXTERNAL",
            employee_id=None,
        )
    )

    assert updated.name == "Electrical Crew A"
    assert updated.cost_type == "EQUIPMENT"
    assert updated.hourly_rate_label == "USD 105.00"

    toggled = api.toggle_resource_active(
        created.id,
        expected_version=resource_service.get_resource(created.id).version,
    )

    assert toggled.is_active is False
    assert toggled.active_label == "Inactive"

    api.delete_resource(created.id)

    assert {resource.id for resource in api.list_resources()} == {employee_resource.id}


def test_project_management_register_desktop_api_mutates_register_entries() -> None:
    project_service = _FakeProjectService()
    project_alpha = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    project_beta = project_service.create_project(
        name="Warehouse Retrofit",
        description="Upgrade lighting and controls.",
    )
    register_service = _FakeRegisterService()
    api = build_project_management_register_desktop_api(
        project_service=project_service,
        register_service=register_service,
    )

    assert [option.label for option in api.list_projects()] == [
        "Plant Upgrade",
        "Warehouse Retrofit",
    ]
    assert api.list_entry_types()[0].value == "RISK"
    assert api.list_statuses()[1].label == "In Progress"
    assert api.list_severities()[0].label == "Low"

    created = api.create_entry(
        SimpleNamespace(
            project_id=project_alpha.id,
            entry_type="RISK",
            title="Critical supplier dependency",
            description="Long-lead switchgear still needs the final release note.",
            severity="CRITICAL",
            status="OPEN",
            owner_name="Lead Planner",
            due_date=date(2026, 5, 2),
            impact_summary="Commissioning could slip by one week.",
            response_plan="Expedite vendor review and approve alternates.",
        )
    )
    api.create_entry(
        SimpleNamespace(
            project_id=project_beta.id,
            entry_type="ISSUE",
            title="Permit handoff blocked",
            description="Permit package is still pending city review.",
            severity="HIGH",
            status="IN_PROGRESS",
            owner_name="Project Engineer",
            due_date=date(2026, 5, 6),
            impact_summary="Site mobilization is at risk.",
            response_plan="Escalate with local authority and track daily.",
        )
    )

    listed = api.list_entries()

    assert created.project_name == "Plant Upgrade"
    assert listed[0].severity_label == "Critical"
    assert listed[0].is_overdue is True

    updated = api.update_entry(
        SimpleNamespace(
            entry_id=created.id,
            project_id=project_alpha.id,
            entry_type="RISK",
            title="Critical supplier dependency mitigated",
            description="Final release note received from the vendor.",
            severity="HIGH",
            status="MITIGATED",
            owner_name="Lead Planner",
            due_date=date(2026, 5, 5),
            impact_summary="Residual risk remains on late freight handling.",
            response_plan="Confirm shipping lane and daily ETA tracking.",
            expected_version=register_service.get_entry(created.id).version,
        )
    )

    assert updated.title == "Critical supplier dependency mitigated"
    assert updated.status == "MITIGATED"
    assert api.list_entries(project_id=project_beta.id)[0].project_name == "Warehouse Retrofit"

    api.delete_entry(created.id)

    assert {entry.id for entry in api.list_entries()} == {"reg-2"}


def test_project_management_financials_desktop_api_mutates_cost_records_and_builds_snapshot() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
        planned_budget=5000.0,
        currency="eur",
    )
    task_service = _FakeTaskService()
    task = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
        priority=90,
        deadline=date(2026, 5, 7),
    )
    cost_service = _FakeCostService()
    finance_service = _FakeFinanceService(
        project_service=project_service,
        task_service=task_service,
        cost_service=cost_service,
    )
    api = build_project_management_financials_desktop_api(
        project_service=project_service,
        task_service=task_service,
        cost_service=cost_service,
        finance_service=finance_service,
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.list_cost_types()[0].value == "LABOR"
    assert api.list_tasks(project.id)[0].label == "Cable Pull"

    created = api.create_cost_item(
        SimpleNamespace(
            project_id=project.id,
            description="Electrical material package",
            planned_amount=1500.0,
            task_id=task.id,
            cost_type="MATERIAL",
            committed_amount=900.0,
            actual_amount=450.0,
            incurred_date=date(2026, 5, 4),
            currency_code="eur",
        )
    )

    listed = api.list_cost_items(project.id)

    assert created.cost_type == "MATERIAL"
    assert listed[0].planned_amount_label == "EUR 1,500.00"
    assert listed[0].task_name == "Cable Pull"

    updated = api.update_cost_item(
        SimpleNamespace(
            cost_id=created.id,
            description="Electrical material package rev A",
            planned_amount=1600.0,
            task_id=task.id,
            cost_type="MATERIAL",
            committed_amount=1000.0,
            actual_amount=650.0,
            incurred_date=date(2026, 5, 5),
            currency_code="usd",
            expected_version=cost_service.get_item(created.id).version,
        )
    )

    assert updated.description == "Electrical material package rev A"
    assert updated.actual_amount_label == "USD 650.00"

    snapshot = api.get_finance_snapshot(project.id)

    assert snapshot.budget_label == "EUR 5,000.00"
    assert snapshot.planned_label == "EUR 1,600.00"
    assert snapshot.ledger[0].reference_label == "Electrical material package rev A"
    assert snapshot.cashflow[0].period_key == "2026-05"
    assert snapshot.by_cost_type[0].label == "Material"
    assert snapshot.notes[0] == "Finance snapshot preview generated from PM financial services."

    api.delete_cost_item(created.id)

    assert api.list_cost_items(project.id) == ()


def test_project_management_tasks_desktop_api_lists_statuses() -> None:
    api = build_project_management_tasks_desktop_api()

    statuses = api.list_statuses()

    assert [status.value for status in statuses] == [
        "TODO",
        "IN_PROGRESS",
        "BLOCKED",
        "DONE",
    ]
    assert statuses[1].label == "In Progress"


def test_project_management_tasks_desktop_api_mutates_task_records() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    api = build_project_management_tasks_desktop_api(
        project_service=project_service,
        task_service=task_service,
    )

    created = api.create_task(
        SimpleNamespace(
            project_id=project.id,
            name="Cable Pull",
            description="Primary feeder cable installation.",
            start_date=date(2026, 5, 3),
            duration_days=4,
            status="IN_PROGRESS",
            priority=80,
            deadline=date(2026, 5, 8),
        )
    )

    listed = api.list_tasks(project.id)

    assert created.project_name == "Plant Upgrade"
    assert created.status == "IN_PROGRESS"
    assert created.status_label == "In Progress"
    assert listed[0].name == "Cable Pull"
    assert listed[0].end_date == date(2026, 5, 6)

    updated = api.update_task(
        SimpleNamespace(
            task_id=created.id,
            expected_version=task_service.get_task(created.id).version,
            name="Cable Pull Rev A",
            description="Updated execution scope.",
            start_date=date(2026, 5, 4),
            duration_days=5,
            status="BLOCKED",
            priority=95,
            deadline=date(2026, 5, 10),
        )
    )

    assert updated.name == "Cable Pull Rev A"
    assert updated.status == "BLOCKED"
    assert updated.deadline == date(2026, 5, 10)

    progressed = api.update_progress(
        SimpleNamespace(
            task_id=created.id,
            expected_version=task_service.get_task(created.id).version,
            percent_complete=65.0,
            actual_start=date(2026, 5, 4),
            actual_end=None,
            status="IN_PROGRESS",
        )
    )

    assert progressed.percent_complete == 65.0
    assert progressed.actual_start == date(2026, 5, 4)
    assert progressed.status == "IN_PROGRESS"

    api.delete_task(created.id)

    assert api.list_tasks(project.id) == ()


def test_project_management_scheduling_desktop_api_supports_schedule_calendar_and_baselines() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    task_a = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
        priority=90,
        deadline=date(2026, 5, 7),
    )
    task_b = task_service.create_task(
        project_id=project.id,
        name="Punchlist Closeout",
        description="Commissioning closeout walkdown.",
        start_date=date(2026, 5, 8),
        duration_days=2,
        priority=50,
        deadline=date(2026, 5, 9),
    )
    scheduling_engine = _FakeSchedulingEngine(
        task_service=task_service,
        critical_task_ids={task_a.id},
    )
    work_calendar_service = _FakeWorkCalendarService()
    work_calendar_engine = _FakeWorkCalendarEngine(work_calendar_service)
    baseline_service = _FakeBaselineService()
    reporting_service = _FakeReportingService()
    api = build_project_management_scheduling_desktop_api(
        project_service=project_service,
        task_service=task_service,
        scheduling_engine=scheduling_engine,
        work_calendar_service=work_calendar_service,
        work_calendar_engine=work_calendar_engine,
        baseline_service=baseline_service,
        reporting_service=reporting_service,
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.get_calendar_snapshot().working_days[0].label == "Mon"

    calendar = api.update_calendar(
        SimpleNamespace(working_days=(0, 1, 2, 3, 4, 5), hours_per_day=10.0)
    )

    assert calendar.hours_per_day == 10.0
    assert calendar.working_days[5].checked is True

    holiday = api.add_holiday(
        SimpleNamespace(holiday_date=date(2026, 5, 1), name="Labor Day")
    )

    assert holiday.name == "Labor Day"
    assert len(api.get_calendar_snapshot().holidays) == 1

    calculation = api.calculate_working_days(
        SimpleNamespace(start_date=date(2026, 5, 4), working_days=3)
    )

    assert calculation.result_date == date(2026, 5, 7)

    schedule = api.list_schedule(project.id)

    assert schedule[0].name == "Cable Pull"
    assert schedule[0].is_critical is True
    assert schedule[1].total_float_days == 2

    created_a = api.create_baseline(
        SimpleNamespace(project_id=project.id, name="Original Plan")
    )
    created_b = api.create_baseline(
        SimpleNamespace(project_id=project.id, name="Weekly Freeze")
    )
    baseline_options = api.list_baselines(project.id)

    assert created_a.value in {option.value for option in baseline_options}
    assert baseline_options[0].value == created_a.value

    comparison_rows = api.compare_baselines(
        project_id=project.id,
        baseline_a_id=created_a.value,
        baseline_b_id=created_b.value,
        include_unchanged=False,
    )

    assert comparison_rows[0].task_name == "Cable Pull"
    assert comparison_rows[0].start_shift_days == 1

    api.delete_holiday(holiday.id)
    api.delete_baseline(created_a.value)

    assert api.get_calendar_snapshot().holidays == ()
    assert [option.value for option in api.list_baselines(project.id)] == [created_b.value]


def test_project_management_portfolio_desktop_api_mutates_portfolio_records() -> None:
    project_service = _FakeProjectService()
    project_alpha = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
        planned_budget=250000.0,
        currency="eur",
    )
    project_beta = project_service.create_project(
        name="Warehouse Retrofit",
        description="Upgrade lighting and controls.",
        planned_budget=120000.0,
        currency="eur",
    )
    project_service.update_project(project_alpha.id, status=ProjectStatus.ACTIVE)
    project_service.update_project(project_beta.id, status=ProjectStatus.ON_HOLD)
    portfolio_service = _FakePortfolioService(project_service)
    api = build_project_management_portfolio_desktop_api(
        project_service=project_service,
        portfolio_service=portfolio_service,
    )

    assert [option.label for option in api.list_projects()] == [
        "Plant Upgrade",
        "Warehouse Retrofit",
    ]
    assert api.list_intake_statuses()[0].value == "PROPOSED"
    assert api.list_dependency_types()[0].label == "Finish -> Start"

    created_template = api.create_scoring_template(
        SimpleNamespace(
            name="Balanced PMO",
            summary="Weighted intake rubric for governance.",
            strategic_weight=3,
            value_weight=2,
            urgency_weight=2,
            risk_weight=1,
            activate=True,
        )
    )
    created_intake = api.create_intake_item(
        SimpleNamespace(
            title="Packaging Line Expansion",
            sponsor_name="Operations Director",
            summary="Capacity uplift on the secondary line.",
            requested_budget=180000.0,
            requested_capacity_percent=40.0,
            target_start_date=date(2026, 6, 1),
            strategic_score=5,
            value_score=4,
            urgency_score=3,
            risk_score=2,
            scoring_template_id=created_template.id,
            status="APPROVED",
        )
    )
    created_scenario = api.create_scenario(
        SimpleNamespace(
            name="Q3 Balanced Plan",
            budget_limit=500000.0,
            capacity_limit_percent=280.0,
            project_ids=(project_alpha.id,),
            intake_item_ids=(created_intake.id,),
            notes="Protect active execution first.",
        )
    )
    comparison_scenario = api.create_scenario(
        SimpleNamespace(
            name="Aggressive Expansion",
            budget_limit=650000.0,
            capacity_limit_percent=340.0,
            project_ids=(project_alpha.id, project_beta.id),
            intake_item_ids=(created_intake.id,),
            notes="Bring forward more intake if labor opens up.",
        )
    )

    listed_templates = api.list_templates()
    listed_intake = api.list_intake_items(status="APPROVED")
    evaluation = api.evaluate_scenario(created_scenario.id)
    comparison = api.compare_scenarios(created_scenario.id, comparison_scenario.id)
    dependency = api.create_project_dependency(
        SimpleNamespace(
            predecessor_project_id=project_alpha.id,
            successor_project_id=project_beta.id,
            dependency_type="FS",
            summary="Warehouse cutover depends on line shutdown lessons learned.",
        )
    )

    assert listed_templates[0].is_active is True
    assert listed_intake[0].title == "Packaging Line Expansion"
    assert evaluation.scenario_name == "Q3 Balanced Plan"
    assert evaluation.status_label == "Within limits"
    assert comparison.added_project_names == ("Warehouse Retrofit",)
    assert dependency.summary == "Warehouse cutover depends on line shutdown lessons learned."
    assert api.list_heatmap()[0].pressure_label in {"Stable", "Watch", "Hot"}
    assert api.list_recent_actions(limit=5)[0].action_label == "Dependency created"

    api.remove_project_dependency(dependency.dependency_id)

    assert api.list_dependencies() == ()


def test_project_management_timesheets_desktop_api_supports_assignment_periods_and_review() -> None:
    project_service = _FakeProjectService()
    project = project_service.create_project(
        name="Plant Upgrade",
        description="Replace switchgear and commission the new line.",
    )
    task_service = _FakeTaskService()
    task = task_service.create_task(
        project_id=project.id,
        name="Cable Pull",
        description="Primary feeder cable installation.",
        start_date=date(2026, 5, 3),
        duration_days=4,
    )
    resource_service = _FakeResourceService()
    resource = resource_service.create_resource(
        name="Electrical Crew",
        role="Lead Technician",
        hourly_rate=95.0,
        is_active=True,
        cost_type=CostType.LABOR,
        currency_code="eur",
        capacity_percent=110.0,
        address="Site Office",
        contact="crew@example.com",
        worker_type=WorkerType.EXTERNAL,
        employee_id=None,
    )
    assignment = task_service.create_assignment(
        task_id=task.id,
        resource_id=resource.id,
        allocation_percent=100.0,
    )
    timesheet_service = _FakeTimesheetService(
        task_service=task_service,
        resource_service=resource_service,
    )
    api = build_project_management_timesheets_desktop_api(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        timesheet_service=timesheet_service,
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.list_queue_statuses()[1].value == "OPEN"
    assert api.list_assignments(project_id=project.id)[0].label == (
        "Plant Upgrade | Cable Pull | Electrical Crew"
    )

    created_entry = api.add_time_entry(
        SimpleNamespace(
            assignment_id=assignment.id,
            entry_date=date(2026, 5, 3),
            hours=8.0,
            note="Cable tray installation",
        )
    )
    api.add_time_entry(
        SimpleNamespace(
            assignment_id=assignment.id,
            entry_date=date(2026, 5, 4),
            hours=6.5,
            note="Termination prep",
        )
    )
    updated_entry = api.update_time_entry(
        SimpleNamespace(
            entry_id=created_entry.entry_id,
            entry_date=date(2026, 5, 3),
            hours=7.5,
            note="Cable tray installation revised",
        )
    )
    snapshot = api.build_assignment_snapshot(assignment.id)
    submitted_period = api.submit_period(
        resource_id=resource.id,
        period_start=date(2026, 5, 1),
        note="Submitted for supervisor review.",
    )
    review_queue = api.list_review_queue()
    review_detail = api.get_review_detail(submitted_period.period_id)
    approved_period = api.approve_period(
        submitted_period.period_id,
        note="Approved after weekly close review.",
    )
    locked_period = api.lock_period(
        resource_id=resource.id,
        period_start=date(2026, 5, 1),
        note="Month-end payroll lock.",
    )
    unlocked_period = api.unlock_period(
        locked_period.period_id,
        note="Reopened for correction.",
    )
    api.delete_time_entry(created_entry.entry_id)

    assert updated_entry.hours_label == "7.50h"
    assert snapshot.assignment.resource_name == "Electrical Crew"
    assert snapshot.entries[0].entry_id == created_entry.entry_id
    assert snapshot.resource_period_total_hours_label == "14.00h"
    assert submitted_period.status == "SUBMITTED"
    assert review_queue[0].entry_count == 2
    assert review_detail.summary.resource_name == "Electrical Crew"
    assert review_detail.entries[0].task_name == "Cable Pull"
    assert approved_period.status == "APPROVED"
    assert locked_period.status == "LOCKED"
    assert unlocked_period.status == "OPEN"
    assert [entry.entry_id for entry in api.build_assignment_snapshot(assignment.id).entries] != [
        created_entry.entry_id
    ]


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


class _FakeProjectService:
    def __init__(self) -> None:
        self._projects: dict[str, Project] = {}
        self._next_id = 1

    def list_projects(self) -> list[Project]:
        return list(self._projects.values())

    def create_project(
        self,
        *,
        name: str,
        description: str = "",
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=ProjectStatus.PLANNED,
            client_name=client_name,
            client_contact=client_contact,
            planned_budget=planned_budget,
            currency=(currency or "").strip().upper() or None,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def update_project(
        self,
        project_id: str,
        *,
        expected_version: int | None = None,
        name: str | None = None,
        description: str | None = None,
        status: ProjectStatus | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        planned_budget: float | None = None,
        currency: str | None = None,
    ) -> Project:
        project = self._projects[project_id]
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if status is not None:
            project.status = status
        if start_date is not None:
            project.start_date = start_date
        if end_date is not None:
            project.end_date = end_date
        if client_name is not None:
            project.client_name = client_name
        if client_contact is not None:
            project.client_contact = client_contact
        if planned_budget is not None:
            project.planned_budget = planned_budget
        if currency is not None:
            project.currency = (currency or "").strip().upper() or None
        project.version += 1
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)


class _FakeCollaborationService:
    def __init__(self) -> None:
        self.marked_task_ids: list[str] = []

    def list_workspace_snapshot(self, *, limit: int = 200) -> SimpleNamespace:
        assert limit == 50
        return SimpleNamespace(
            notifications=[
                SimpleNamespace(
                    notification_type="approval",
                    entity_type="approval_request",
                    entity_id="approval-1",
                    headline="Approval requested for Weekly Freeze",
                    body_preview="Baseline comparison needs governance review.",
                    actor_username="alex",
                    created_at=datetime(2026, 5, 1, 9, 30),
                    project_id="proj-1",
                    project_name="Plant Upgrade",
                    attention=True,
                )
            ],
            inbox=[
                SimpleNamespace(
                    comment_id="comment-1",
                    task_id="task-1",
                    task_name="Cable Pull",
                    project_id="proj-1",
                    project_name="Plant Upgrade",
                    author_username="jamie",
                    body_preview="Please review the updated execution window.",
                    mentions=["planner"],
                    created_at=datetime(2026, 5, 1, 8, 45),
                    unread=True,
                )
            ],
            recent_activity=[
                SimpleNamespace(
                    comment_id="comment-2",
                    task_id="task-2",
                    task_name="Commissioning Pack",
                    project_id="proj-1",
                    project_name="Plant Upgrade",
                    author_username="morgan",
                    body_preview="Draft punchlist is now linked for review.",
                    mentions=[],
                    created_at=datetime(2026, 5, 1, 8, 15),
                    unread=False,
                )
            ],
            active_presence=[
                SimpleNamespace(
                    task_id="task-1",
                    task_name="Cable Pull",
                    project_id="proj-1",
                    project_name="Plant Upgrade",
                    username="planner",
                    display_name="Alex Taylor",
                    activity="reviewing",
                    last_seen_at=datetime(2026, 5, 1, 9, 35),
                    is_self=True,
                )
            ],
        )

    def mark_task_mentions_read(self, task_id: str) -> None:
        self.marked_task_ids.append(task_id)


class _FakeEmployeeService:
    def __init__(self) -> None:
        self._employees = [
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

    def list_employees(self, *, active_only: bool | None = None) -> list[SimpleNamespace]:
        if active_only is None:
            return list(self._employees)
        return [
            employee
            for employee in self._employees
            if bool(employee.is_active) == bool(active_only)
        ]

    def get_employee(self, employee_id: str) -> SimpleNamespace | None:
        return next((employee for employee in self._employees if employee.id == employee_id), None)


class _FakeResourceService:
    def __init__(self) -> None:
        self._resources: dict[str, SimpleNamespace] = {}
        self._next_id = 1
        self._employee_service = _FakeEmployeeService()

    def list_resources(self) -> list[SimpleNamespace]:
        return list(self._resources.values())

    def create_resource(
        self,
        *,
        name: str,
        role: str = "",
        hourly_rate: float = 0.0,
        is_active: bool = True,
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType = WorkerType.EXTERNAL,
        employee_id: str | None = None,
    ) -> SimpleNamespace:
        employee = self._employee_service.get_employee(employee_id) if employee_id else None
        resource = SimpleNamespace(
            id=f"res-{self._next_id}",
            name=employee.full_name if employee is not None else name,
            role=employee.title if employee is not None else role,
            hourly_rate=hourly_rate,
            is_active=is_active,
            cost_type=cost_type,
            currency_code=(currency_code or "").strip().upper() or None,
            version=1,
            capacity_percent=capacity_percent,
            address=address,
            contact=(employee.email or employee.phone or "") if employee is not None else contact,
            worker_type=worker_type,
            employee_id=employee_id,
        )
        self._next_id += 1
        self._resources[resource.id] = resource
        return resource

    def update_resource(
        self,
        resource_id: str,
        *,
        name: str | None = None,
        role: str | None = None,
        hourly_rate: float | None = None,
        is_active: bool | None = None,
        cost_type: CostType | None = None,
        currency_code: str | None = None,
        capacity_percent: float | None = None,
        address: str | None = None,
        contact: str | None = None,
        worker_type: WorkerType | None = None,
        employee_id: str | None = None,
        expected_version: int | None = None,
    ) -> SimpleNamespace:
        resource = self._resources[resource_id]
        if name is not None:
            resource.name = name
        if role is not None:
            resource.role = role
        if hourly_rate is not None:
            resource.hourly_rate = hourly_rate
        if is_active is not None:
            resource.is_active = is_active
        if cost_type is not None:
            resource.cost_type = cost_type
        if currency_code is not None:
            resource.currency_code = (currency_code or "").strip().upper() or None
        if capacity_percent is not None:
            resource.capacity_percent = capacity_percent
        if address is not None:
            resource.address = address
        if contact is not None:
            resource.contact = contact
        if worker_type is not None:
            resource.worker_type = worker_type
        if employee_id is not None:
            employee = self._employee_service.get_employee(employee_id)
            resource.employee_id = employee_id
            if employee is not None:
                resource.name = employee.full_name
                resource.role = employee.title
                resource.contact = employee.email or employee.phone or ""
        elif worker_type == WorkerType.EXTERNAL:
            resource.employee_id = None
        resource.version += 1
        return resource

    def get_resource(self, resource_id: str) -> SimpleNamespace:
        return self._resources[resource_id]

    def delete_resource(self, resource_id: str) -> None:
        del self._resources[resource_id]


class _FakeRegisterService:
    def __init__(self) -> None:
        self._entries: dict[str, SimpleNamespace] = {}
        self._next_id = 1

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

    def create_entry(
        self,
        project_id: str,
        *,
        entry_type: RegisterEntryType,
        title: str,
        description: str = "",
        severity: RegisterEntrySeverity = RegisterEntrySeverity.MEDIUM,
        status: RegisterEntryStatus = RegisterEntryStatus.OPEN,
        owner_name: str | None = None,
        due_date: date | None = None,
        impact_summary: str = "",
        response_plan: str = "",
    ) -> SimpleNamespace:
        entry = SimpleNamespace(
            id=f"reg-{self._next_id}",
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
            version=1,
        )
        self._next_id += 1
        self._entries[entry.id] = entry
        return entry

    def update_entry(
        self,
        entry_id: str,
        *,
        expected_version: int | None = None,
        entry_type: RegisterEntryType | None = None,
        title: str | None = None,
        description: str | None = None,
        severity: RegisterEntrySeverity | None = None,
        status: RegisterEntryStatus | None = None,
        owner_name: str | None = None,
        due_date: date | None = None,
        impact_summary: str | None = None,
        response_plan: str | None = None,
    ) -> SimpleNamespace:
        entry = self._entries[entry_id]
        if entry_type is not None:
            entry.entry_type = entry_type
        if title is not None:
            entry.title = title
        if description is not None:
            entry.description = description
        if severity is not None:
            entry.severity = severity
        if status is not None:
            entry.status = status
        if owner_name is not None:
            entry.owner_name = owner_name
        entry.due_date = due_date
        if impact_summary is not None:
            entry.impact_summary = impact_summary
        if response_plan is not None:
            entry.response_plan = response_plan
        entry.version += 1
        return entry

    def delete_entry(self, entry_id: str) -> None:
        del self._entries[entry_id]

    def get_entry(self, entry_id: str) -> SimpleNamespace:
        return self._entries[entry_id]


class _FakeTaskService:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._assignments: dict[str, TaskAssignment] = {}
        self._next_id = 1

    def list_tasks_for_project(self, project_id: str) -> list[Task]:
        return [task for task in self._tasks.values() if task.project_id == project_id]

    def create_task(
        self,
        *,
        project_id: str,
        name: str,
        description: str = "",
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int = 0,
        deadline: date | None = None,
    ) -> Task:
        task = Task(
            id=f"task-{self._next_id}",
            project_id=project_id,
            name=name,
            description=description,
            start_date=start_date,
            end_date=_derive_end_date(start_date, duration_days),
            duration_days=duration_days,
            priority=priority,
            deadline=deadline,
        )
        self._next_id += 1
        self._tasks[task.id] = task
        return task

    def create_assignment(
        self,
        *,
        task_id: str,
        resource_id: str,
        allocation_percent: float = 100.0,
        hours_logged: float = 0.0,
    ) -> TaskAssignment:
        assignment = TaskAssignment(
            id=f"assign-{len(self._assignments) + 1}",
            task_id=task_id,
            resource_id=resource_id,
            allocation_percent=allocation_percent,
            hours_logged=hours_logged,
        )
        self._assignments[assignment.id] = assignment
        return assignment

    def list_assignments_for_tasks(self, task_ids: list[str]) -> list[TaskAssignment]:
        task_id_set = {str(task_id) for task_id in task_ids}
        return [
            assignment
            for assignment in self._assignments.values()
            if assignment.task_id in task_id_set
        ]

    def get_assignment(self, assignment_id: str) -> TaskAssignment | None:
        return self._assignments.get(assignment_id)

    def update_task(
        self,
        task_id: str,
        *,
        expected_version: int | None = None,
        name: str | None = None,
        description: str | None = None,
        status: TaskStatus | None = None,
        start_date: date | None = None,
        duration_days: int | None = None,
        priority: int | None = None,
        deadline: date | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if name is not None:
            task.name = name
        if description is not None:
            task.description = description
        if status is not None:
            task.status = status
        if start_date is not None:
            task.start_date = start_date
        if duration_days is not None:
            task.duration_days = duration_days
        if priority is not None:
            task.priority = priority
        if deadline is not None:
            task.deadline = deadline
        task.end_date = _derive_end_date(task.start_date, task.duration_days)
        task.version += 1
        return task

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1

    def update_progress(
        self,
        task_id: str,
        *,
        percent_complete: float | None = None,
        actual_start: date | None = None,
        actual_end: date | None = None,
        status: TaskStatus | None = None,
        expected_version: int | None = None,
    ) -> Task:
        task = self._tasks[task_id]
        if percent_complete is not None:
            task.percent_complete = percent_complete
        if actual_start is not None:
            task.actual_start = actual_start
        if actual_end is not None:
            task.actual_end = actual_end
        if status is not None:
            task.status = status
        task.version += 1
        return task

    def delete_task(self, task_id: str) -> None:
        del self._tasks[task_id]

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)


class _FakePortfolioService:
    def __init__(self, project_service: _FakeProjectService) -> None:
        self._project_service = project_service
        self._templates: dict[str, PortfolioScoringTemplate] = {}
        self._intake_items: dict[str, PortfolioIntakeItem] = {}
        self._scenarios: dict[str, PortfolioScenario] = {}
        self._dependencies: dict[str, PortfolioProjectDependency] = {}
        self._actions: list[PortfolioRecentAction] = []

    def list_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        return list(self._templates.values())

    def create_scoring_template(
        self,
        *,
        name: str,
        summary: str = "",
        strategic_weight: int = 3,
        value_weight: int = 2,
        urgency_weight: int = 2,
        risk_weight: int = 1,
        activate: bool = False,
    ) -> PortfolioScoringTemplate:
        if activate:
            for existing in self._templates.values():
                existing.is_active = False
        template = PortfolioScoringTemplate(
            id=f"tpl-{len(self._templates) + 1}",
            name=name,
            summary=summary,
            strategic_weight=strategic_weight,
            value_weight=value_weight,
            urgency_weight=urgency_weight,
            risk_weight=risk_weight,
            is_active=activate,
            created_at=datetime(2026, 5, 1, 9, 0),
            updated_at=datetime(2026, 5, 1, 9, 0),
        )
        self._templates[template.id] = template
        self._append_action("Template created", "Portfolio", summary or name)
        return template

    def activate_scoring_template(self, template_id: str) -> PortfolioScoringTemplate:
        for existing in self._templates.values():
            existing.is_active = existing.id == template_id
        template = self._templates[template_id]
        self._append_action("Template activated", "Portfolio", template.name)
        return template

    def list_intake_items(
        self,
        *,
        status: PortfolioIntakeStatus | None = None,
    ) -> list[PortfolioIntakeItem]:
        rows = list(self._intake_items.values())
        if status is not None:
            rows = [row for row in rows if row.status == status]
        return rows

    def create_intake_item(
        self,
        *,
        title: str,
        sponsor_name: str,
        summary: str = "",
        requested_budget: float = 0.0,
        requested_capacity_percent: float = 0.0,
        target_start_date: date | None = None,
        strategic_score: int = 3,
        value_score: int = 3,
        urgency_score: int = 3,
        risk_score: int = 3,
        scoring_template_id: str | None = None,
        status: PortfolioIntakeStatus = PortfolioIntakeStatus.PROPOSED,
    ) -> PortfolioIntakeItem:
        template = (
            self._templates.get(str(scoring_template_id or "").strip())
            if scoring_template_id
            else next((row for row in self._templates.values() if row.is_active), None)
        )
        item = PortfolioIntakeItem(
            id=f"intake-{len(self._intake_items) + 1}",
            title=title,
            sponsor_name=sponsor_name,
            summary=summary,
            requested_budget=requested_budget,
            requested_capacity_percent=requested_capacity_percent,
            target_start_date=target_start_date,
            strategic_score=strategic_score,
            value_score=value_score,
            urgency_score=urgency_score,
            risk_score=risk_score,
            scoring_template_id=template.id if template is not None else "",
            scoring_template_name=template.name if template is not None else "Balanced PMO",
            strategic_weight=getattr(template, "strategic_weight", 3),
            value_weight=getattr(template, "value_weight", 2),
            urgency_weight=getattr(template, "urgency_weight", 2),
            risk_weight=getattr(template, "risk_weight", 1),
            status=status,
            created_at=datetime(2026, 5, 1, 10, 0),
            updated_at=datetime(2026, 5, 1, 10, 0),
            version=1,
        )
        self._intake_items[item.id] = item
        self._append_action("Intake created", "Portfolio", item.title)
        return item

    def list_scenarios(self) -> list[PortfolioScenario]:
        return list(self._scenarios.values())

    def create_scenario(
        self,
        *,
        name: str,
        budget_limit: float | None = None,
        capacity_limit_percent: float | None = None,
        project_ids: list[str] | None = None,
        intake_item_ids: list[str] | None = None,
        notes: str = "",
    ) -> PortfolioScenario:
        scenario = PortfolioScenario(
            id=f"scn-{len(self._scenarios) + 1}",
            name=name,
            budget_limit=budget_limit,
            capacity_limit_percent=capacity_limit_percent,
            project_ids=list(project_ids or []),
            intake_item_ids=list(intake_item_ids or []),
            notes=notes,
            created_at=datetime(2026, 5, 2, 9, 0),
            updated_at=datetime(2026, 5, 2, 9, 0),
        )
        self._scenarios[scenario.id] = scenario
        self._append_action("Scenario saved", "Portfolio", scenario.name)
        return scenario

    def evaluate_scenario(self, scenario_id: str) -> PortfolioScenarioEvaluation:
        scenario = self._scenarios[scenario_id]
        selected_projects = [
            self._project_service.get_project(project_id)
            for project_id in scenario.project_ids
        ]
        selected_items = [
            self._intake_items[item_id]
            for item_id in scenario.intake_item_ids
            if item_id in self._intake_items
        ]
        project_budget = sum(
            float(getattr(project, "planned_budget", 0.0) or 0.0)
            for project in selected_projects
            if project is not None
        )
        intake_budget = sum(float(item.requested_budget or 0.0) for item in selected_items)
        total_budget = project_budget + intake_budget
        total_capacity = sum(
            float(item.requested_capacity_percent or 0.0) for item in selected_items
        )
        capacity_limit = scenario.capacity_limit_percent
        available_capacity = max(float(capacity_limit or 0.0) - total_capacity, 0.0)
        over_budget = (
            scenario.budget_limit is not None and total_budget > float(scenario.budget_limit)
        )
        over_capacity = capacity_limit is not None and total_capacity > float(capacity_limit)
        return PortfolioScenarioEvaluation(
            scenario_id=scenario.id,
            scenario_name=scenario.name,
            selected_projects=len([project for project in selected_projects if project is not None]),
            selected_intake_items=len(selected_items),
            total_budget=total_budget,
            budget_limit=scenario.budget_limit,
            total_capacity_percent=total_capacity,
            capacity_limit_percent=capacity_limit,
            available_capacity_percent=available_capacity,
            intake_composite_score=sum(item.composite_score for item in selected_items),
            over_budget=over_budget,
            over_capacity=over_capacity,
            summary=(
                "Within limits"
                if not over_budget and not over_capacity
                else "Escalation required"
            ),
        )

    def compare_scenarios(
        self,
        base_scenario_id: str,
        candidate_scenario_id: str,
    ) -> PortfolioScenarioComparison:
        base = self._scenarios[base_scenario_id]
        candidate = self._scenarios[candidate_scenario_id]
        base_eval = self.evaluate_scenario(base_scenario_id)
        candidate_eval = self.evaluate_scenario(candidate_scenario_id)
        base_project_ids = set(base.project_ids)
        candidate_project_ids = set(candidate.project_ids)
        base_intake_ids = set(base.intake_item_ids)
        candidate_intake_ids = set(candidate.intake_item_ids)
        return PortfolioScenarioComparison(
            base_scenario_id=base.id,
            base_scenario_name=base.name,
            candidate_scenario_id=candidate.id,
            candidate_scenario_name=candidate.name,
            base_evaluation=base_eval,
            candidate_evaluation=candidate_eval,
            budget_delta=candidate_eval.total_budget - base_eval.total_budget,
            capacity_delta_percent=(
                candidate_eval.total_capacity_percent - base_eval.total_capacity_percent
            ),
            intake_score_delta=(
                candidate_eval.intake_composite_score - base_eval.intake_composite_score
            ),
            selected_projects_delta=(
                candidate_eval.selected_projects - base_eval.selected_projects
            ),
            selected_intake_items_delta=(
                candidate_eval.selected_intake_items - base_eval.selected_intake_items
            ),
            added_project_names=[
                self._project_service.get_project(project_id).name
                for project_id in sorted(candidate_project_ids - base_project_ids)
                if self._project_service.get_project(project_id) is not None
            ],
            removed_project_names=[
                self._project_service.get_project(project_id).name
                for project_id in sorted(base_project_ids - candidate_project_ids)
                if self._project_service.get_project(project_id) is not None
            ],
            added_intake_titles=[
                self._intake_items[item_id].title
                for item_id in sorted(candidate_intake_ids - base_intake_ids)
                if item_id in self._intake_items
            ],
            removed_intake_titles=[
                self._intake_items[item_id].title
                for item_id in sorted(base_intake_ids - candidate_intake_ids)
                if item_id in self._intake_items
            ],
            summary="Candidate scenario increases scope and portfolio demand.",
        )

    def list_portfolio_heatmap(self) -> list[PortfolioExecutiveRow]:
        rows: list[PortfolioExecutiveRow] = []
        for project in self._project_service.list_projects():
            pressure_label = "Hot" if project.status == ProjectStatus.ON_HOLD else "Stable"
            rows.append(
                PortfolioExecutiveRow(
                    project_id=project.id,
                    project_name=project.name,
                    project_status=project.status.value,
                    late_tasks=1 if pressure_label == "Hot" else 0,
                    critical_tasks=1,
                    peak_utilization_percent=118.0 if pressure_label == "Hot" else 92.0,
                    cost_variance=-8500.0 if pressure_label == "Hot" else 2500.0,
                    pressure_score=90 if pressure_label == "Hot" else 40,
                    pressure_label=pressure_label,
                )
            )
        return rows

    def list_project_dependencies(self) -> list[PortfolioProjectDependencyView]:
        rows: list[PortfolioProjectDependencyView] = []
        for dependency in self._dependencies.values():
            predecessor = self._project_service.get_project(dependency.predecessor_project_id)
            successor = self._project_service.get_project(dependency.successor_project_id)
            rows.append(
                PortfolioProjectDependencyView(
                    dependency_id=dependency.id,
                    predecessor_project_id=dependency.predecessor_project_id,
                    predecessor_project_name=getattr(
                        predecessor,
                        "name",
                        dependency.predecessor_project_id,
                    ),
                    predecessor_project_status=getattr(
                        getattr(predecessor, "status", None),
                        "value",
                        "PLANNED",
                    ),
                    successor_project_id=dependency.successor_project_id,
                    successor_project_name=getattr(
                        successor,
                        "name",
                        dependency.successor_project_id,
                    ),
                    successor_project_status=getattr(
                        getattr(successor, "status", None),
                        "value",
                        "PLANNED",
                    ),
                    dependency_type=dependency.dependency_type,
                    summary=dependency.summary,
                    pressure_label="Watch",
                    created_at=dependency.created_at,
                )
            )
        return rows

    def create_project_dependency(
        self,
        *,
        predecessor_project_id: str,
        successor_project_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        summary: str = "",
    ) -> PortfolioProjectDependency:
        dependency = PortfolioProjectDependency(
            id=f"dep-{len(self._dependencies) + 1}",
            predecessor_project_id=predecessor_project_id,
            successor_project_id=successor_project_id,
            dependency_type=dependency_type,
            summary=summary,
            created_at=datetime(2026, 5, 3, 8, 45),
            updated_at=datetime(2026, 5, 3, 8, 45),
        )
        self._dependencies[dependency.id] = dependency
        self._append_action(
            "Dependency created",
            getattr(
                self._project_service.get_project(predecessor_project_id),
                "name",
                predecessor_project_id,
            ),
            summary or dependency.id,
        )
        return dependency

    def remove_project_dependency(self, dependency_id: str) -> None:
        self._dependencies.pop(dependency_id, None)
        self._append_action("Dependency removed", "Portfolio", dependency_id)

    def list_recent_pm_actions(self, *, limit: int = 12) -> list[PortfolioRecentAction]:
        return list(reversed(self._actions[-limit:]))

    def _append_action(self, action_label: str, project_name: str, summary: str) -> None:
        self._actions.append(
            PortfolioRecentAction(
                occurred_at=datetime(2026, 5, 3, 9, len(self._actions)),
                project_name=project_name,
                actor_username="alex",
                action_label=action_label,
                summary=summary,
            )
        )


class _FakeTimesheetService:
    def __init__(
        self,
        *,
        task_service: _FakeTaskService,
        resource_service: _FakeResourceService,
    ) -> None:
        self._task_service = task_service
        self._resource_service = resource_service
        self._entries: dict[str, TimeEntry] = {}
        self._periods: dict[tuple[str, date], TimesheetPeriod] = {}

    def list_time_entries_for_assignment(self, assignment_id: str) -> list[TimeEntry]:
        return [
            entry
            for entry in self._entries.values()
            if entry.assignment_id == assignment_id
        ]

    def list_time_entries_for_assignment_period(
        self,
        assignment_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return [
            entry
            for entry in self.list_time_entries_for_assignment(assignment_id)
            if entry.entry_date.year == period_start.year
            and entry.entry_date.month == period_start.month
        ]

    def list_time_entries_for_resource_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> list[TimeEntry]:
        return [
            entry
            for entry in self._entries.values()
            if self._resource_id_for_entry(entry) == resource_id
            and entry.entry_date.year == period_start.year
            and entry.entry_date.month == period_start.month
        ]

    def list_timesheet_periods_for_resource(self, resource_id: str) -> list[TimesheetPeriod]:
        return [
            period
            for (current_resource_id, _period_start), period in self._periods.items()
            if current_resource_id == resource_id
        ]

    def get_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
    ) -> TimesheetPeriod:
        return self._ensure_period(resource_id, period_start)

    def add_time_entry(
        self,
        assignment_id: str,
        *,
        entry_date: date,
        hours: float,
        note: str = "",
    ) -> TimeEntry:
        assignment = self._task_service.get_assignment(assignment_id)
        task = self._task_service.get_task(assignment.task_id) if assignment is not None else None
        entry = TimeEntry(
            id=f"entry-{len(self._entries) + 1}",
            work_allocation_id=assignment_id,
            assignment_id=assignment_id,
            entry_date=entry_date,
            hours=float(hours),
            note=note,
            author_username="alex",
            owner_type="task_assignment",
            owner_id=getattr(task, "id", None),
            owner_label=getattr(task, "name", assignment_id),
            scope_type="project",
            scope_id=getattr(task, "project_id", None),
        )
        self._entries[entry.id] = entry
        self._ensure_period(assignment.resource_id, entry_date.replace(day=1))
        return entry

    def update_time_entry(
        self,
        entry_id: str,
        *,
        entry_date: date | None = None,
        hours: float | None = None,
        note: str | None = None,
    ) -> TimeEntry:
        entry = self._entries[entry_id]
        if entry_date is not None:
            entry.entry_date = entry_date
        if hours is not None:
            entry.hours = float(hours)
        if note is not None:
            entry.note = note
        return entry

    def delete_time_entry(self, entry_id: str) -> None:
        del self._entries[entry_id]

    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        period = self._ensure_period(resource_id, period_start)
        period.status = TimesheetPeriodStatus.SUBMITTED
        period.submitted_at = datetime(2026, 5, 4, 17, 0)
        period.submitted_by_username = "alex"
        period.decision_note = note
        return period

    def approve_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime(2026, 5, 5, 9, 0)
        period.decided_by_username = "jamie"
        period.decision_note = note
        return period

    def reject_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime(2026, 5, 5, 9, 0)
        period.decided_by_username = "jamie"
        period.decision_note = note
        return period

    def lock_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        period = self._ensure_period(resource_id, period_start)
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime(2026, 5, 6, 18, 0)
        period.decision_note = note
        return period

    def unlock_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        period = self._period_by_id(period_id)
        period.status = TimesheetPeriodStatus.OPEN
        period.decision_note = note
        period.locked_at = None
        return period

    def list_timesheet_review_queue(
        self,
        *,
        status: TimesheetPeriodStatus | None = TimesheetPeriodStatus.SUBMITTED,
        limit: int = 200,
    ) -> list[SimpleNamespace]:
        rows: list[SimpleNamespace] = []
        for period in self._periods.values():
            if status is not None and period.status != status:
                continue
            rows.append(self._build_review_summary(period))
        return rows[:limit]

    def get_timesheet_review_detail(self, period_id: str) -> SimpleNamespace:
        period = self._period_by_id(period_id)
        summary = self._build_review_summary(period)
        entries = self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        review_entries = []
        for entry in entries:
            assignment = self._task_service.get_assignment(entry.assignment_id or "")
            task = self._task_service.get_task(assignment.task_id) if assignment is not None else None
            review_entries.append(
                SimpleNamespace(
                    entry_id=entry.id,
                    entry_date=entry.entry_date,
                    hours=float(entry.hours or 0.0),
                    note=entry.note or "",
                    author_username=entry.author_username,
                    task_name=getattr(task, "name", entry.owner_label or ""),
                    project_id=getattr(task, "project_id", None),
                )
            )
        return SimpleNamespace(summary=summary, entries=tuple(review_entries))

    def _build_review_summary(self, period: TimesheetPeriod) -> SimpleNamespace:
        entries = self.list_time_entries_for_resource_period(
            period.resource_id,
            period_start=period.period_start,
        )
        resource = self._resource_service.get_resource(period.resource_id)
        project_ids = sorted(
            {
                entry.scope_id
                for entry in entries
                if getattr(entry, "scope_type", None) == "project" and getattr(entry, "scope_id", None)
            }
        )
        return SimpleNamespace(
            period_id=period.id,
            resource_id=period.resource_id,
            resource_name=getattr(resource, "name", period.resource_id),
            period_start=period.period_start,
            period_end=period.period_end,
            status=period.status,
            submitted_at=period.submitted_at,
            submitted_by_username=period.submitted_by_username,
            decided_at=period.decided_at,
            decided_by_username=period.decided_by_username,
            decision_note=period.decision_note,
            entry_count=len(entries),
            total_hours=sum(float(entry.hours or 0.0) for entry in entries),
            project_ids=tuple(project_ids),
        )

    def _ensure_period(self, resource_id: str, period_start: date) -> TimesheetPeriod:
        key = (resource_id, period_start)
        if key not in self._periods:
            self._periods[key] = TimesheetPeriod(
                id=f"period-{len(self._periods) + 1}",
                resource_id=resource_id,
                period_start=period_start,
                period_end=_test_period_end(period_start),
            )
        return self._periods[key]

    def _period_by_id(self, period_id: str) -> TimesheetPeriod:
        for period in self._periods.values():
            if period.id == period_id:
                return period
        raise KeyError(period_id)

    def _resource_id_for_entry(self, entry: TimeEntry) -> str | None:
        assignment = self._task_service.get_assignment(entry.assignment_id or "")
        return assignment.resource_id if assignment is not None else None


class _FakeCostService:
    def __init__(self) -> None:
        self._items: dict[str, SimpleNamespace] = {}
        self._next_id = 1

    def list_cost_items_for_project(self, project_id: str) -> list[SimpleNamespace]:
        return [
            item for item in self._items.values() if item.project_id == project_id
        ]

    def add_cost_item(
        self,
        project_id: str,
        *,
        description: str,
        planned_amount: float,
        task_id: str | None = None,
        cost_type: CostType = CostType.OVERHEAD,
        committed_amount: float = 0.0,
        actual_amount: float = 0.0,
        incurred_date: date | None = None,
        currency_code: str | None = None,
    ) -> SimpleNamespace:
        item = SimpleNamespace(
            id=f"cost-{self._next_id}",
            project_id=project_id,
            task_id=task_id,
            description=description,
            planned_amount=planned_amount,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            cost_type=cost_type,
            incurred_date=incurred_date,
            currency_code=(currency_code or "").strip().upper() or None,
            version=1,
        )
        self._next_id += 1
        self._items[item.id] = item
        return item

    def update_cost_item(
        self,
        cost_id: str,
        *,
        description: str | None = None,
        planned_amount: float | None = None,
        committed_amount: float | None = None,
        actual_amount: float | None = None,
        cost_type: CostType | None = None,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        expected_version: int | None = None,
    ) -> SimpleNamespace:
        item = self._items[cost_id]
        if description is not None:
            item.description = description
        if planned_amount is not None:
            item.planned_amount = planned_amount
        if committed_amount is not None:
            item.committed_amount = committed_amount
        if actual_amount is not None:
            item.actual_amount = actual_amount
        if cost_type is not None:
            item.cost_type = cost_type
        if incurred_date is not None:
            item.incurred_date = incurred_date
        if currency_code is not None:
            item.currency_code = (currency_code or "").strip().upper() or None
        item.version += 1
        return item

    def delete_cost_item(self, cost_id: str) -> None:
        del self._items[cost_id]

    def get_item(self, cost_id: str) -> SimpleNamespace:
        return self._items[cost_id]


class _FakeFinanceService:
    def __init__(
        self,
        *,
        project_service: _FakeProjectService,
        task_service: _FakeTaskService,
        cost_service: _FakeCostService,
    ) -> None:
        self._project_service = project_service
        self._task_service = task_service
        self._cost_service = cost_service

    def get_finance_snapshot(self, project_id: str) -> SimpleNamespace:
        project = self._project_service.get_project(project_id)
        items = self._cost_service.list_cost_items_for_project(project_id)
        budget = float(getattr(project, "planned_budget", 0.0) or 0.0)
        planned = sum(float(item.planned_amount or 0.0) for item in items)
        committed = sum(float(item.committed_amount or 0.0) for item in items)
        actual = sum(float(item.actual_amount or 0.0) for item in items)
        exposure = max(committed, actual)
        available = budget - exposure if budget > 0.0 else None
        task_lookup = {
            task.id: task.name for task in self._task_service.list_tasks_for_project(project_id)
        }
        ledger = [
            SimpleNamespace(
                project_id=project_id,
                source_key=f"source-{item.id}",
                source_label="Direct Cost",
                cost_type=item.cost_type.value,
                stage="actual" if float(item.actual_amount or 0.0) > 0.0 else "planned",
                amount=float(item.actual_amount or item.planned_amount or 0.0),
                currency=item.currency_code or getattr(project, "currency", None),
                occurred_on=item.incurred_date,
                reference_type="cost_item",
                reference_id=item.id,
                reference_label=item.description,
                task_id=item.task_id,
                task_name=task_lookup.get(item.task_id or "", None),
                resource_id=None,
                resource_name=None,
                included_in_policy=True,
            )
            for item in items
        ]
        cashflow = [
            SimpleNamespace(
                period_key="2026-05",
                period_start=date(2026, 5, 1),
                period_end=date(2026, 5, 31),
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=max(planned, committed),
                exposure=max(committed, actual),
            )
        ]
        by_source = [
            SimpleNamespace(
                dimension="source",
                key="direct_cost",
                label="Direct Cost",
                planned=planned,
                committed=committed,
                actual=actual,
                forecast=max(planned, committed),
                exposure=max(committed, actual),
            )
        ]
        by_cost_type_totals: dict[str, dict[str, float]] = {}
        for item in items:
            bucket = by_cost_type_totals.setdefault(
                item.cost_type.value,
                {
                    "planned": 0.0,
                    "committed": 0.0,
                    "actual": 0.0,
                },
            )
            bucket["planned"] += float(item.planned_amount or 0.0)
            bucket["committed"] += float(item.committed_amount or 0.0)
            bucket["actual"] += float(item.actual_amount or 0.0)
        by_cost_type = [
            SimpleNamespace(
                dimension="cost_type",
                key=key,
                label=key.replace("_", " ").title(),
                planned=totals["planned"],
                committed=totals["committed"],
                actual=totals["actual"],
                forecast=max(totals["planned"], totals["committed"]),
                exposure=max(totals["committed"], totals["actual"]),
            )
            for key, totals in by_cost_type_totals.items()
        ]
        return SimpleNamespace(
            project_id=project_id,
            project_currency=getattr(project, "currency", None),
            budget=budget,
            planned=planned,
            committed=committed,
            actual=actual,
            exposure=exposure,
            available=available,
            ledger=ledger,
            cashflow=cashflow,
            by_source=by_source,
            by_cost_type=by_cost_type,
            by_resource=[],
            by_task=[],
            notes=["Finance snapshot preview generated from PM financial services."],
        )


class _FakeSchedulingEngine:
    def __init__(
        self,
        *,
        task_service: _FakeTaskService,
        critical_task_ids: set[str],
    ) -> None:
        self._task_service = task_service
        self._critical_task_ids = critical_task_ids

    def recalculate_project_schedule(
        self,
        project_id: str,
        *,
        persist: bool = True,
    ) -> dict[str, SimpleNamespace]:
        result: dict[str, SimpleNamespace] = {}
        for task in self._task_service.list_tasks_for_project(project_id):
            total_float_days = 0 if task.id in self._critical_task_ids else 2
            result[task.id] = SimpleNamespace(
                task=task,
                earliest_start=task.start_date,
                earliest_finish=task.end_date,
                latest_start=task.start_date if total_float_days == 0 else date.fromordinal(task.start_date.toordinal() + total_float_days),
                latest_finish=task.end_date if total_float_days == 0 else date.fromordinal(task.end_date.toordinal() + total_float_days),
                total_float_days=total_float_days,
                is_critical=task.id in self._critical_task_ids,
                deadline=task.deadline,
                late_by_days=0 if task.id in self._critical_task_ids else 1,
            )
        return result


class _FakeWorkCalendarService:
    def __init__(self) -> None:
        self._working_days = {0, 1, 2, 3, 4}
        self._hours_per_day = 8.0
        self._holidays: dict[str, SimpleNamespace] = {}
        self._next_holiday_id = 1

    def get_calendar(self) -> SimpleNamespace:
        return SimpleNamespace(
            working_days=set(self._working_days),
            hours_per_day=self._hours_per_day,
        )

    def set_working_days(self, working_days: set[int], hours_per_day: float | None = None):
        self._working_days = set(working_days)
        if hours_per_day is not None:
            self._hours_per_day = hours_per_day
        return self.get_calendar()

    def list_holidays(self) -> list[SimpleNamespace]:
        return list(self._holidays.values())

    def add_holiday(self, holiday_date: date, name: str = "") -> SimpleNamespace:
        holiday = SimpleNamespace(
            id=f"holiday-{self._next_holiday_id}",
            date=holiday_date,
            name=name,
        )
        self._next_holiday_id += 1
        self._holidays[holiday.id] = holiday
        return holiday

    def delete_holiday(self, holiday_id: str) -> None:
        del self._holidays[holiday_id]


class _FakeWorkCalendarEngine:
    def __init__(self, work_calendar_service: _FakeWorkCalendarService) -> None:
        self._service = work_calendar_service

    def add_working_days(self, start_date: date, working_days: int) -> date:
        current = start_date
        added = 0
        while added < working_days:
            current = date.fromordinal(current.toordinal() + 1)
            if self.is_working_day(current):
                added += 1
        return current

    def is_working_day(self, target_date: date) -> bool:
        holiday_dates = {holiday.date for holiday in self._service.list_holidays()}
        return (
            target_date.weekday() in self._service.get_calendar().working_days
            and target_date not in holiday_dates
        )


class _FakeBaselineService:
    def __init__(self) -> None:
        self._baselines_by_project: dict[str, list[SimpleNamespace]] = {}
        self._next_id = 1

    def list_baselines(self, project_id: str) -> list[SimpleNamespace]:
        return list(self._baselines_by_project.get(project_id, []))

    def create_baseline(self, project_id: str, name: str = "Baseline") -> SimpleNamespace:
        baseline = SimpleNamespace(
            id=f"base-{self._next_id}",
            project_id=project_id,
            name=name,
            created_at=date(2026, 5, self._next_id),
        )
        self._next_id += 1
        self._baselines_by_project.setdefault(project_id, []).append(baseline)
        return baseline

    def delete_baseline(self, baseline_id: str) -> None:
        for project_id, baselines in self._baselines_by_project.items():
            self._baselines_by_project[project_id] = [
                baseline for baseline in baselines if baseline.id != baseline_id
            ]


class _FakeReportingService:
    def compare_baselines(
        self,
        *,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
        include_unchanged: bool = False,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            rows=[
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
        )


def _test_period_end(period_start: date) -> date:
    if period_start.month == 12:
        return date.fromordinal(date(period_start.year + 1, 1, 1).toordinal() - 1)
    return date.fromordinal(
        date(period_start.year, period_start.month + 1, 1).toordinal() - 1
    )


def _derive_end_date(
    start_date: date | None,
    duration_days: int | None,
) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
