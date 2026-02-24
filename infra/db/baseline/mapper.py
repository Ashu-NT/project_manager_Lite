from __future__ import annotations

from core.models import BaselineTask, ProjectBaseline
from infra.db.models import BaselineTaskORM, ProjectBaselineORM


def baseline_from_orm(obj: ProjectBaselineORM) -> ProjectBaseline:
    return ProjectBaseline(
        id=obj.id,
        project_id=obj.project_id,
        name=obj.name,
        created_at=obj.created_at,
    )


def baseline_to_orm(baseline: ProjectBaseline) -> ProjectBaselineORM:
    return ProjectBaselineORM(
        id=baseline.id,
        project_id=baseline.project_id,
        name=baseline.name,
        created_at=baseline.created_at,
    )


def baseline_task_from_orm(obj: BaselineTaskORM) -> BaselineTask:
    return BaselineTask(
        id=obj.id,
        baseline_id=obj.baseline_id,
        task_id=obj.task_id,
        task_name=obj.task_name,
        baseline_start=obj.baseline_start,
        baseline_finish=obj.baseline_finish,
        baseline_duration_days=obj.baseline_duration_days,
        baseline_planned_cost=obj.baseline_planned_cost,
    )


def baseline_task_to_orm(task: BaselineTask) -> BaselineTaskORM:
    return BaselineTaskORM(
        id=task.id,
        baseline_id=task.baseline_id,
        task_id=task.task_id,
        task_name=task.task_name,
        baseline_start=task.baseline_start,
        baseline_finish=task.baseline_finish,
        baseline_duration_days=task.baseline_duration_days,
        baseline_planned_cost=task.baseline_planned_cost,
    )


__all__ = [
    "baseline_from_orm",
    "baseline_to_orm",
    "baseline_task_from_orm",
    "baseline_task_to_orm",
]
