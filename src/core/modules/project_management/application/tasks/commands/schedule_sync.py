from __future__ import annotations

from src.core.modules.project_management.application.scheduling import SchedulingEngine


class TaskScheduleSyncMixin:
    _scheduling_engine: SchedulingEngine | None

    def _sync_project_schedule(self, project_id: str | None) -> None:
        if not project_id:
            return
        scheduler: SchedulingEngine = getattr(self, "_scheduling_engine", None)
        if scheduler is None:
            return
        scheduler.recalculate_project_schedule(project_id)


__all__ = ["TaskScheduleSyncMixin"]
