"""Constraint violation view-model assembly."""

import logging

from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintViolation,
)
from src.core.modules.project_management.domain.tasks.hierarchy import select_leaf_tasks

logger = logging.getLogger(__name__)

def build_constraint_violations(
    project_id: str,
    *,
    scheduling_engine=None,
    task_service=None,
    constraint_validator=None,
) -> tuple[ConstraintViolation, ...]:
    if not project_id or scheduling_engine is None or task_service is None or constraint_validator is None:
        return ()
    try:
        schedule = scheduling_engine.recalculate_project_schedule(project_id, persist=False)
        tasks = select_leaf_tasks(task_service.list_tasks_for_project(project_id))
        tasks_by_id = {t.id: t for t in tasks}
        result = constraint_validator.validate(tasks_by_id, schedule)
        return tuple(result.violations)
    except Exception:
        logger.exception("Failed to build constraint violations for project_id=%s", project_id)
        return ()


__all__ = ["build_constraint_violations"]
