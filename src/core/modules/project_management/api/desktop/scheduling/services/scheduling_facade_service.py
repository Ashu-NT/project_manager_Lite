"""Scheduling orchestration helpers."""

from datetime import date

from src.core.modules.project_management.api.desktop.scheduling.models.schedule import SchedulingTaskDto
from src.core.modules.project_management.api.desktop.scheduling.serializers.schedule_serializer import (
    serialize_schedule_item,
    serialize_task_as_schedule_item,
)


def build_schedule_from_engine(project_id: str, scheduling_engine, persist: bool) -> tuple[SchedulingTaskDto, ...]:
    schedule = scheduling_engine.recalculate_project_schedule(project_id, persist=persist)
    items = sorted(
        schedule.values(),
        key=lambda info: (
            info.earliest_start or date.max,
            0 if info.is_critical else 1,
            (info.task.name or "").casefold(),
        ),
    )
    return tuple(serialize_schedule_item(item) for item in items)


def build_schedule_from_tasks(project_id: str, task_service) -> tuple[SchedulingTaskDto, ...]:
    if task_service is None:
        return ()
    tasks = sorted(
        task_service.list_tasks_for_project(project_id),
        key=lambda t: (t.start_date or date.max, (t.name or "").casefold()),
    )
    return tuple(serialize_task_as_schedule_item(t) for t in tasks)


__all__ = ["build_schedule_from_engine", "build_schedule_from_tasks"]
