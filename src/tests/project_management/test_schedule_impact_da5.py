from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.scheduling.cpm.cpm_calculator import (
    CPMResult,
)
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.domain.tasks.task import Task


class _TaskRepository:
    def __init__(self, task: Task) -> None:
        self._task = task

    def list_by_project(self, project_id: str) -> list[Task]:
        return [self._task] if project_id == self._task.project_id else []


class _DependencyRepository:
    @staticmethod
    def list_by_project(_project_id: str) -> list:
        return []


class _Calendar:
    @staticmethod
    def working_days_between(start: date, end: date) -> int:
        return abs((end - start).days) + 1


class _BaselineLookup:
    def __init__(self) -> None:
        self.project_ids: list[str] = []

    def get_approved_baseline(self, project_id: str) -> object:
        self.project_ids.append(project_id)
        return object()


class _CpmSequence:
    def __init__(self) -> None:
        self._results = iter(
            (
                CPMResult({}, date(2026, 8, 10), []),
                CPMResult({}, date(2026, 8, 12), []),
                CPMResult({}, date(2026, 8, 10), []),
                CPMResult({}, date(2026, 8, 12), []),
            )
        )

    def calculate(self, _tasks_by_id, _dependencies) -> CPMResult:
        return next(self._results)


def test_schedule_impact_service_owns_baseline_resolution_for_all_scenarios() -> None:
    task = Task(
        id="task-1",
        project_id="project-1",
        name="Commissioning",
        wbs_code="1",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 5),
        duration_days=5,
    )
    baseline_lookup = _BaselineLookup()
    service = ScheduleChangeImpactService(
        task_repo=_TaskRepository(task),
        dependency_repo=_DependencyRepository(),
        calendar=_Calendar(),
        baseline_lookup=baseline_lookup,
        approval_threshold_days=1,
    )
    service._cpm = _CpmSequence()

    explicit = service.analyse(
        project_id=task.project_id,
        changed_task_id=task.id,
        proposed_start=date(2026, 8, 2),
    )
    delayed = service.analyse_delay(
        project_id=task.project_id,
        changed_task_id=task.id,
        current_start=task.start_date,
        delay_days=1,
    )

    assert explicit.requires_approval is True
    assert delayed.requires_approval is True
    assert baseline_lookup.project_ids == [task.project_id, task.project_id]
