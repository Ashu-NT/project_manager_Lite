from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.project_management.application.scheduling import SchedulingEngine


def emit_cascade_schedule_changed(uow, *, scope, project_id: str, changed_task_ids: list[str]) -> None:
    """One `TaskScheduleChanged(CASCADE_RECALCULATED)` per sibling Task whose
    schedule genuinely changed as a downstream consequence of another
    operation's `_sync_project_schedule` call -- never a synthetic bulk fact.
    Shared by every caller of `_sync_project_schedule` (dependency add/update/
    remove, scheduling-constraint update, resource-leveling apply, approved
    schedule changes)."""
    if not changed_task_ids:
        return
    from src.core.modules.project_management.application.tasks.task_events import (
        TaskScheduleChangeType,
        TaskScheduleChanged,
    )

    for task_id in changed_task_ids:
        uow.record_event(
            TaskScheduleChanged(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                task_id=task_id,
                change_type=TaskScheduleChangeType.CASCADE_RECALCULATED,
                occurred_at=datetime.now(timezone.utc),
            )
        )


class TaskScheduleSyncMixin:
    _scheduling_engine: SchedulingEngine | None

    def _sync_project_schedule(
        self,
        project_id: str | None,
        *,
        commit: bool = True,
        exclude_task_ids: frozenset[str] = frozenset(),
    ) -> list[str]:
        """Recalculates the project's CPM schedule and returns the ids of
        every Task whose persisted `start_date`/`end_date` actually changed,
        excluding `exclude_task_ids` (tasks the caller already recorded its
        own primary `TaskScheduleChanged` fact for). Callers use this to
        emit `TaskScheduleChanged(CASCADE_RECALCULATED)` for genuine sibling
        schedule changes, one fact per actually-changed Task, never a
        synthetic bulk fact. The before/after diff is computed here as a
        thin wrapper -- `SchedulingEngine.recalculate_project_schedule`
        itself is unaffected."""
        if not project_id:
            return []
        scheduler: SchedulingEngine = getattr(self, "_scheduling_engine", None)
        if scheduler is None:
            return []
        task_repo = getattr(self, "_task_repo", None)
        before: dict[str, tuple] = {}
        if task_repo is not None:
            before = {
                task.id: (task.start_date, task.end_date)
                for task in task_repo.list_by_project(project_id)
            }
        scheduler.recalculate_project_schedule(project_id, commit=commit)
        if task_repo is None or not before:
            return []
        changed_ids: list[str] = []
        for task in task_repo.list_by_project(project_id):
            if task.id in exclude_task_ids:
                continue
            previous = before.get(task.id)
            if previous is None:
                continue
            if previous != (task.start_date, task.end_date):
                changed_ids.append(task.id)
        return changed_ids


__all__ = ["TaskScheduleSyncMixin"]
