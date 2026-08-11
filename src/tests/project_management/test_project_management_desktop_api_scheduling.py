from datetime import date, datetime, timedelta
from types import SimpleNamespace

from src.core.modules.project_management.api.desktop import (
    build_project_management_scheduling_desktop_api,
)
from src.core.modules.project_management.domain.enums import (
    DependencyType,
    ProjectStatus,
    TaskStatus,
)
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.domain.tasks.task import Task
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintValidator,
)


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
        constraint_validator=ConstraintValidator(work_calendar_engine),
    )

    assert api.list_projects()[0].label == "Plant Upgrade"
    assert api.get_calendar_snapshot().working_days[0].label == "Mon"

    calculation = api.calculate_working_days(
        SimpleNamespace(start_date=date(2026, 5, 4), working_days=3)
    )

    assert calculation.result_date == date(2026, 5, 7)

    schedule = api.list_schedule(project.id)

    assert schedule[0].name == "Cable Pull"
    assert schedule[0].is_critical is True
    assert schedule[1].total_float_days == 2
    assert api.list_constraint_violations(project.id) == ()

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

    api.delete_baseline(created_a.value)

    assert api.get_calendar_snapshot().holidays == ()
    assert [option.value for option in api.list_baselines(project.id)] == [created_b.value]


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
        status: "ProjectStatus | None" = None,
        client_name: str | None = None,
        client_contact: str | None = None,
        financial_currency_code: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> Project:
        project = Project(
            id=f"proj-{self._next_id}",
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status=status if status is not None else ProjectStatus.PLANNED,
            client_name=client_name,
            client_contact=client_contact,
            version=1,
        )
        self._next_id += 1
        self._projects[project.id] = project
        return project

    def get_project(self, project_id: str) -> Project | None:
        return self._projects.get(project_id)

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
        project.version += 1
        return project

    def set_status(self, project_id: str, status: ProjectStatus) -> None:
        self._projects[project_id].status = status
        self._projects[project_id].version += 1

    def delete_project(self, project_id: str) -> None:
        del self._projects[project_id]


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
        code: str = "",
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
            code=code,
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

    def get_task(self, task_id: str) -> Task | None:
        return self._tasks.get(task_id)

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks[task_id]
        task.status = status
        task.version += 1


class _FakeSchedulingEngine:
    def __init__(self, *, task_service: _FakeTaskService, critical_task_ids: set[str]) -> None:
        self._task_service = task_service
        self._critical_task_ids = critical_task_ids

    def recalculate_project_schedule(self, project_id: str, *, persist: bool = True) -> dict[str, SimpleNamespace]:
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
        return SimpleNamespace(working_days=set(self._working_days), hours_per_day=self._hours_per_day)

    def set_working_days(self, working_days: set[int], hours_per_day: float | None = None):
        self._working_days = set(working_days)
        if hours_per_day is not None:
            self._hours_per_day = hours_per_day
        return self.get_calendar()

    def list_holidays(self) -> list[SimpleNamespace]:
        return list(self._holidays.values())

    def add_holiday(self, holiday_date: date, name: str = "") -> SimpleNamespace:
        holiday = SimpleNamespace(id=f"holiday-{self._next_holiday_id}", date=holiday_date, name=name)
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

    def create_baseline(
        self, project_id: str, name: str = "Baseline", *, rate_as_of: date | None = None
    ) -> SimpleNamespace:
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
            self._baselines_by_project[project_id] = [b for b in baselines if b.id != baseline_id]


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


def _derive_end_date(start_date: date | None, duration_days: int | None) -> date | None:
    if start_date is None or duration_days is None:
        return None
    return start_date + timedelta(days=max(duration_days - 1, 0))
