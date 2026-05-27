from __future__ import annotations

from datetime import date, timedelta

from src.core.modules.project_management.application.dashboard.models import (
    CriticalPathRow,
    MilestoneHealthRow,
)
from src.core.modules.project_management.application.scheduling import CPMTaskInfo
from src.core.modules.project_management.application.tasks import TaskService


class DashboardProfessionalMixin:
    _tasks: TaskService

    def _build_milestone_health(
        self,
        project_id: str,
        *,
        schedule: dict[str, CPMTaskInfo] | None = None,
    ) -> list[MilestoneHealthRow]:
        tasks = self._tasks.list_tasks_for_project(project_id)
        if not tasks:
            return []
        info_by_id = schedule or self._sched.recalculate_project_schedule(project_id, persist=False)
        owner_by_task = self._build_task_owner_map(tasks)
        milestone_tasks = [task for task in tasks if self._is_explicit_milestone(task)]
        if not milestone_tasks:
            milestone_tasks = [
                task
                for task in tasks
                if task.deadline is not None or getattr(info_by_id.get(task.id), "earliest_finish", None) is not None
            ]

        rows: list[MilestoneHealthRow] = []
        for task in sorted(
            milestone_tasks,
            key=lambda item: (self._milestone_target(item, info_by_id) or date.max, item.name.lower()),
        )[:8]:
            info = info_by_id.get(task.id)
            target_date = self._milestone_target(task, info_by_id)
            if target_date is None:
                continue
            rows.append(
                MilestoneHealthRow(
                    task_id=task.id,
                    task_name=task.name,
                    owner_name=owner_by_task.get(task.id),
                    target_date=target_date,
                    status_label=self._milestone_status(task, info, target_date),
                    slip_days=getattr(info, "late_by_days", None),
                )
            )
        return rows

    def _build_critical_watchlist(
        self,
        project_id: str,
        *,
        schedule: dict[str, CPMTaskInfo] | None = None,
    ) -> list[CriticalPathRow]:
        tasks = self._tasks.list_tasks_for_project(project_id)
        if not tasks:
            return []
        info_by_id = schedule or self._sched.recalculate_project_schedule(project_id, persist=False)
        owner_by_task = self._build_task_owner_map(tasks)
        watch_candidates = [
            info
            for info in info_by_id.values()
            if not self._is_done(info.task) and info.earliest_finish is not None
        ]
        critical = [info for info in watch_candidates if bool(info.is_critical)]
        selected = critical or sorted(
            watch_candidates,
            key=lambda info: (
                info.total_float_days is None,
                info.total_float_days if info.total_float_days is not None else 9999,
                info.earliest_finish or date.max,
                -int(getattr(info.task, "priority", 0) or 0),
            ),
        )

        rows: list[CriticalPathRow] = []
        for info in selected[:8]:
            task = info.task
            rows.append(
                CriticalPathRow(
                    task_id=task.id,
                    task_name=task.name,
                    owner_name=owner_by_task.get(task.id),
                    finish_date=info.earliest_finish,
                    total_float_days=info.total_float_days,
                    late_by_days=info.late_by_days,
                    status_label=self._watchlist_status(info),
                )
            )
        return rows

    def _build_task_owner_map(self, tasks: list[object]) -> dict[str, str | None]:
        owner_by_task: dict[str, str | None] = {}
        resource_names = {
            resource.id: resource.name
            for resource in getattr(self, "_resources").list_resources()
        }
        for task in tasks:
            assignments = self._tasks.list_assignments_for_task(task.id)
            if not assignments:
                owner_by_task[task.id] = None
                continue
            primary = max(assignments, key=lambda item: float(item.allocation_percent or 0.0))
            resource_id = getattr(primary, "resource_id", None)
            owner_by_task[task.id] = getattr(primary, "resource_name", None) or resource_names.get(resource_id) or resource_id
        return owner_by_task

    @staticmethod
    def _is_explicit_milestone(task: object) -> bool:
        name = str(getattr(task, "name", "") or "").strip().lower()
        duration = getattr(task, "duration_days", None)
        return duration == 0 or "milestone" in name or "gate" in name

    @staticmethod
    def _milestone_target(task: object, info_by_id: dict[str, CPMTaskInfo]) -> date | None:
        info = info_by_id.get(getattr(task, "id", ""))
        return getattr(task, "deadline", None) or getattr(info, "earliest_finish", None) or getattr(task, "end_date", None) or getattr(task, "start_date", None)

    @staticmethod
    def _is_done(task: object) -> bool:
        raw = getattr(task, "status", "")
        value = getattr(raw, "value", raw)
        return str(value).strip().upper() == "DONE"

    def _milestone_status(self, task: object, info: CPMTaskInfo | None, target_date: date) -> str:
        if self._is_done(task):
            return "Done"
        if info is not None and int(info.late_by_days or 0) > 0:
            return "Late"
        today = date.today()
        if target_date < today:
            return "Late"
        if target_date <= today + timedelta(days=7):
            return "Due Soon"
        if info is not None and bool(info.is_critical):
            return "Critical"
        return "On Track"

    @staticmethod
    def _watchlist_status(info: CPMTaskInfo) -> str:
        raw = getattr(info.task, "status", "")
        value = getattr(raw, "value", raw)
        status = str(value).strip().upper()
        if status == "BLOCKED":
            return "Blocked"
        if int(info.late_by_days or 0) > 0:
            return "Late"
        if bool(info.is_critical):
            return "Critical"
        return "Tight Float"


__all__ = ["DashboardProfessionalMixin"]
