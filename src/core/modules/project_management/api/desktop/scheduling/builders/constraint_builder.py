"""Constraint violation view-model assembly."""

from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import ConstraintValidator
from src.core.modules.project_management.api.desktop.scheduling.models.constraints import SchedulingConstraintViolationDto
from src.core.modules.project_management.api.desktop.scheduling.serializers.constraint_serializer import serialize_constraint_violation


def build_constraint_violations(
    project_id: str,
    *,
    scheduling_engine=None,
    task_service=None,
    work_calendar_engine=None,
) -> tuple[SchedulingConstraintViolationDto, ...]:
    if not project_id or scheduling_engine is None or task_service is None or work_calendar_engine is None:
        return ()
    try:
        schedule = scheduling_engine.recalculate_project_schedule(project_id, persist=False)
        tasks = task_service.list_tasks_for_project(project_id)
        tasks_by_id = {t.id: t for t in tasks}
        validator = ConstraintValidator(calendar=work_calendar_engine)
        result = validator.validate(tasks_by_id, schedule)
        hard_pairs = {(v.task_id, v.constraint_type) for v in result.hard_violations}
        return tuple(serialize_constraint_violation(v, hard_pairs=hard_pairs) for v in result.violations)
    except Exception:
        return ()


__all__ = ["build_constraint_violations"]
