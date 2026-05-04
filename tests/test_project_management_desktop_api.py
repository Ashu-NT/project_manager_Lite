from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
    build_project_management_workspace_desktop_api,
)
from src.core.modules.project_management.domain.enums import CostType, ProjectStatus, TaskStatus, WorkerType
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
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


def _derive_end_date(
    start_date: date | None,
    duration_days: int | None,
) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
