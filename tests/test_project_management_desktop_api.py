from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_dashboard_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_workspace_desktop_api,
)
from src.core.modules.project_management.domain.enums import ProjectStatus
from src.core.modules.project_management.domain.projects.project import Project
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
