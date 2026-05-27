from __future__ import annotations

from datetime import datetime

from src.core.modules.project_management.domain.scheduling.baseline import (
    BaselineStatus,
    BaselineTask,
    BaselineVarianceRecord,
    ProjectBaseline,
)
from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    BaselineVarianceRecordORM,
    ProjectBaselineORM,
)


def _as_date(value):
    if isinstance(value, datetime):
        return value.date()
    return value


def baseline_from_orm(obj: ProjectBaselineORM) -> ProjectBaseline:
    status_raw = obj.status or BaselineStatus.DRAFT.value
    return ProjectBaseline(
        id=obj.id,
        project_id=obj.project_id,
        name=obj.name,
        created_at=_as_date(obj.created_at),
        status=BaselineStatus(status_raw),
        version=int(obj.version or 1),
        submitted_by=obj.submitted_by,
        submitted_at=obj.submitted_at,
        approved_by=obj.approved_by,
        approved_at=obj.approved_at,
        notes=obj.notes or "",
    )


def baseline_to_orm(baseline: ProjectBaseline) -> ProjectBaselineORM:
    return ProjectBaselineORM(
        id=baseline.id,
        project_id=baseline.project_id,
        name=baseline.name,
        created_at=baseline.created_at,
        status=baseline.status.value,
        version=baseline.version,
        submitted_by=baseline.submitted_by,
        submitted_at=baseline.submitted_at,
        approved_by=baseline.approved_by,
        approved_at=baseline.approved_at,
        notes=baseline.notes or None,
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


def variance_record_from_orm(obj: BaselineVarianceRecordORM) -> BaselineVarianceRecord:
    return BaselineVarianceRecord(
        id=obj.id,
        project_id=obj.project_id,
        new_baseline_id=obj.new_baseline_id,
        superseded_baseline_id=obj.superseded_baseline_id,
        task_id=obj.task_id,
        task_name=obj.task_name,
        start_variance_days=obj.start_variance_days,
        finish_variance_days=obj.finish_variance_days,
        cost_variance=obj.cost_variance,
        created_at=obj.created_at,
    )


def variance_record_to_orm(record: BaselineVarianceRecord) -> BaselineVarianceRecordORM:
    return BaselineVarianceRecordORM(
        id=record.id,
        project_id=record.project_id,
        new_baseline_id=record.new_baseline_id,
        superseded_baseline_id=record.superseded_baseline_id,
        task_id=record.task_id,
        task_name=record.task_name,
        start_variance_days=record.start_variance_days,
        finish_variance_days=record.finish_variance_days,
        cost_variance=record.cost_variance,
        created_at=record.created_at,
    )


__all__ = [
    "baseline_from_orm",
    "baseline_to_orm",
    "baseline_task_from_orm",
    "baseline_task_to_orm",
    "variance_record_from_orm",
    "variance_record_to_orm",
]
