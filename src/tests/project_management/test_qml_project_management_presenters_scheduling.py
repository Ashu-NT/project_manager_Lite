from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import ProjectManagementWorkspaceCatalog
from src.core.modules.project_management.api.desktop import (
    build_project_management_scheduling_desktop_api,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    ProjectBaseline,
)
from src.core.modules.project_management.domain.tasks.task import Task


class _FakeSchedulingEngine:
    def __init__(self, schedules: dict[str, list[SimpleNamespace]]) -> None:
        self._schedules = schedules

    def recalculate_project_schedule(self, project_id: str, *, persist: bool = True) -> dict[str, SimpleNamespace]:
        return {item.task.id: item for item in self._schedules.get(project_id, [])}


class _FakeWorkCalendarService:
    def get_calendar(self) -> SimpleNamespace:
        return SimpleNamespace(working_days={0, 1, 2, 3, 4}, hours_per_day=8.0)

    def list_holidays(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(id="holiday-1", date=date(2026, 5, 1), name="Labor Day")]


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

    def compare_baselines(self, *, project_id, baseline_a_id, baseline_b_id, include_unchanged=False) -> SimpleNamespace:
        return SimpleNamespace(
            rows=list(self._rows_by_key.get((project_id, baseline_a_id, baseline_b_id, include_unchanged), []))
        )


def _build_schedule_record(
    *,
    task_id,
    project_id,
    name,
    status,
    start_date,
    finish_date,
    latest_start,
    latest_finish,
    total_float_days,
    is_critical,
    deadline,
    late_by_days,
    percent_complete,
) -> SimpleNamespace:
    return SimpleNamespace(
        task=Task(
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


def _approved_baseline(
    baseline_id: str,
    name: str,
    created_at: date,
) -> ProjectBaseline:
    return ProjectBaseline(
        id=baseline_id,
        project_id="proj-1",
        name=name,
        created_at=created_at,
        status=BaselineStatus.APPROVED,
        submitted_by="planner",
        submitted_at=created_at,
        approved_by="reviewer",
        approved_at=created_at,
    )


def test_project_management_workspace_catalog_exposes_typed_scheduling_controller() -> None:
    scheduling_api = build_project_management_scheduling_desktop_api(
        project_service=SimpleNamespace(
            list_projects=lambda: [
                SimpleNamespace(id="proj-1", name="Plant Upgrade", organization_id="org-1"),
                SimpleNamespace(id="proj-2", name="Warehouse Retrofit", organization_id="org-1"),
            ],
            get_project=lambda project_id: SimpleNamespace(
                id=project_id,
                organization_id="org-1",
            ),
        ),
        task_service=SimpleNamespace(list_tasks_for_project=lambda project_id: []),
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
                    _approved_baseline(
                        "base-2",
                        "Weekly Freeze",
                        date(2026, 5, 7),
                    ),
                    _approved_baseline(
                        "base-1",
                        "Original Plan",
                        date(2026, 5, 1),
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
                        planned_cost_delta="1200",
                    )
                ]
            }
        ),
        tenant_context_service=SimpleNamespace(
            require_active_scope_ids=lambda **_kwargs: SimpleNamespace(
                tenant_id="tenant-1",
                organization_id="org-1",
            )
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
    assert controller.ganttRowsModel.row_for_task("task-1").name == "Cable Pull"
    assert controller.criticalPath["items"][0]["title"] == "Cable Pull"
    assert controller.baselines["rows"][0]["title"] == "Cable Pull"

    controller.setActivitySort("taskName", 1)

    assert controller.activitySortKey == "taskName"
    assert controller.activitySortDirection == 1
    assert [row.name for row in controller.ganttRowsModel.effective_rows] == [
        "Punchlist Closeout",
        "Cable Pull",
    ]

    controller.selectProject("proj-2")

    assert controller.selectedProjectId == "proj-2"
    assert controller.ganttRowsModel.rowCountValue == 0
