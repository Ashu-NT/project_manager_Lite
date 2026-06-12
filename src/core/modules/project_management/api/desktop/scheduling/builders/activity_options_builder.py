from datetime import date
from src.core.modules.project_management.api.desktop.scheduling.models.schedule import SchedulingProjectOptionDescriptor


def build_activity_options(
    project_id: str,
    task_service=None,
    *,
    exclude_task_id: str | None = None,
) -> tuple[SchedulingProjectOptionDescriptor, ...]:
    normalized_project_id = (project_id or "").strip()
    if not normalized_project_id or task_service is None:
        return ()
    excluded = (exclude_task_id or "").strip()
    tasks = sorted(
        task_service.list_tasks_for_project(normalized_project_id),
        key=lambda t: (t.start_date or date.max, (t.name or "").casefold()),
    )
    return tuple(
        SchedulingProjectOptionDescriptor(value=t.id, label=t.name)
        for t in tasks
        if t.id != excluded
    )


__all__ = ["build_activity_options"]
