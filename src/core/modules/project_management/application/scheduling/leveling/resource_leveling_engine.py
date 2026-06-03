from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from sqlalchemy.orm import Session

from src.core.modules.project_management.contracts.repositories.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.application.scheduling.models.leveling import (
    ResourceConflict,
    ResourceLevelingAction,
    ResourceLevelingResult,
)
from src.core.modules.project_management.application.scheduling.leveling.leveling import (
    build_resource_conflicts,
    build_successors_map,
    choose_auto_level_task,
)
from src.core.modules.project_management.domain.tasks.task import Task, TaskAssignment
from src.core.platform.common.exceptions import BusinessRuleError, ValidationError


class ResourceLevelingEngine:
    """
    Proper standalone resource leveling service.

    Replaces the ResourceLevelingMixin pattern — all leveling operations go
    through this class instead of being bolted onto SchedulingEngine.

    Designed to:
    - preview conflicts without persisting anything
    - propose leveling actions (non-destructive simulation)
    - apply leveling only when explicitly committed by the application service
    - never silently rewrite an approved schedule
    """

    def __init__(
        self,
        session: Session,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        resource_repo: ResourceRepository,
        calendar: CalendarProtocol,
    ) -> None:
        self._session = session
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._assignment_repo = assignment_repo
        self._resource_repo = resource_repo
        self._calendar = calendar
        self._resource_threshold_by_id: dict[str, float] = {}

    # ── conflict preview (read-only) ────────────────────────────────────────

    def preview_conflicts(
        self,
        project_id: str,
        threshold_percent: float = 100.0,
    ) -> list[ResourceConflict]:
        """Return all resource overloads without persisting anything."""
        if threshold_percent <= 0:
            raise ValidationError(
                "threshold_percent must be greater than zero.",
                code="RESOURCE_LEVELING_INVALID_THRESHOLD",
            )
        tasks = self._task_repo.list_by_project(project_id)
        if not tasks:
            return []
        assignments = self._list_assignments(tasks)
        if not assignments:
            return []
        resource_names = self._build_resource_name_map(assignments, threshold_percent)
        return build_resource_conflicts(
            tasks_by_id={t.id: t for t in tasks},
            assignments=assignments,
            calendar=self._calendar,
            resource_name_by_id=resource_names,
            threshold_percent=threshold_percent,
            threshold_by_resource_id=self._resource_threshold_by_id,
        )

    # ── simulation (non-destructive) ────────────────────────────────────────

    def simulate_auto_level(
        self,
        project_id: str,
        max_iterations: int = 60,
        threshold_percent: float = 100.0,
    ) -> ResourceLevelingResult:
        """
        Simulate leveling and return proposed actions WITHOUT writing to DB.

        The caller decides whether to commit the returned actions.
        """
        if max_iterations <= 0:
            raise ValidationError(
                "max_iterations must be positive.",
                code="RESOURCE_LEVELING_INVALID_ITERATIONS",
            )

        initial_conflicts = self.preview_conflicts(project_id, threshold_percent)
        tasks = self._task_repo.list_by_project(project_id)
        # Work on in-memory copies so the simulation never mutates stored state
        from dataclasses import replace
        tasks_by_id: dict[str, Task] = {t.id: replace(t) for t in tasks}

        actions: list[ResourceLevelingAction] = []
        successors = build_successors_map(self._dependency_repo.list_by_project(project_id))
        iterations = 0

        while iterations < max_iterations:
            assignments = self._list_assignments(list(tasks_by_id.values()))
            if not assignments:
                break
            resource_names = self._build_resource_name_map(assignments, threshold_percent)
            conflicts = build_resource_conflicts(
                tasks_by_id=tasks_by_id,
                assignments=assignments,
                calendar=self._calendar,
                resource_name_by_id=resource_names,
                threshold_percent=threshold_percent,
                threshold_by_resource_id=self._resource_threshold_by_id,
            )
            if not conflicts:
                break

            top = max(conflicts, key=lambda c: (c.total_allocation_percent, len(c.entries)))
            task_id = choose_auto_level_task(
                conflict=top,
                tasks_by_id=tasks_by_id,
                successors_by_task_id=successors,
                priority_value=self._priority_value,
            )
            if task_id is None:
                break

            task = tasks_by_id[task_id]
            action = self._shift_task(
                task=task,
                shift_working_days=1,
                reason=(
                    f"Auto-leveling: resolved {top.total_allocation_percent:.1f}% "
                    f"overload on {top.conflict_date.isoformat()}"
                ),
                resource_id=top.resource_id,
                resource_name=top.resource_name,
                conflict_date=top.conflict_date,
            )
            actions.append(action)
            iterations += 1

        final_conflicts = build_resource_conflicts(
            tasks_by_id=tasks_by_id,
            assignments=self._list_assignments(list(tasks_by_id.values())),
            calendar=self._calendar,
            resource_name_by_id={},
            threshold_percent=threshold_percent,
            threshold_by_resource_id=self._resource_threshold_by_id,
        ) if actions else initial_conflicts

        return ResourceLevelingResult(
            conflicts_before=len(initial_conflicts),
            conflicts_after=len(final_conflicts),
            iterations=iterations,
            actions=actions,
        )

    # ── commit (writes to DB) ────────────────────────────────────────────────

    def commit_actions(self, actions: list[ResourceLevelingAction]) -> None:
        """
        Apply a list of previously simulated leveling actions to the task store.

        Raises BusinessRuleError if any task has acquired actual dates since simulation.
        """
        for action in actions:
            task = self._task_repo.get(action.task_id)
            if task is None:
                continue
            if getattr(task, "actual_start", None) or getattr(task, "actual_end", None):
                raise BusinessRuleError(
                    f"Cannot apply leveling to task '{task.name}': task already has actual dates.",
                    code="RESOURCE_LEVELING_LOCKED_TASK",
                )
            task.start_date = action.new_start
            task.end_date = action.new_end
            try:
                self._task_repo.update(task)
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise

    # ── internal ────────────────────────────────────────────────────────────

    def _shift_task(
        self,
        task: Task,
        shift_working_days: int,
        reason: str,
        resource_id: str | None,
        resource_name: str | None,
        conflict_date,
    ) -> ResourceLevelingAction:
        from src.core.platform.common.exceptions import ValidationError as VE
        old_start = task.start_date
        old_end = task.end_date
        if old_start is None:
            raise VE("Task must have a start date.", code="RESOURCE_LEVELING_NO_START")
        new_start = self._calendar.add_working_days(old_start, shift_working_days + 1)
        duration = int(task.duration_days or 0)
        new_end = new_start if duration <= 0 else self._calendar.add_working_days(new_start, duration)
        task.start_date = new_start
        task.end_date = new_end
        return ResourceLevelingAction(
            task_id=task.id,
            task_name=task.name,
            resource_id=resource_id,
            resource_name=resource_name,
            conflict_date=conflict_date,
            shift_working_days=shift_working_days,
            old_start=old_start,
            old_end=old_end,
            new_start=new_start,
            new_end=new_end,
            reason=reason,
        )

    def _list_assignments(self, tasks: list[Task]) -> list[TaskAssignment]:
        task_ids = [t.id for t in tasks]
        return self._assignment_repo.list_by_tasks(task_ids) if task_ids else []

    def _build_resource_name_map(
        self,
        assignments: list[TaskAssignment],
        threshold_percent: float,
    ) -> dict[str, str]:
        scale = float(threshold_percent or 100.0) / 100.0
        self._resource_threshold_by_id = {}
        names: dict[str, str] = {}
        for asgn in assignments:
            rid = asgn.resource_id
            if rid in names:
                continue
            resource = self._resource_repo.get(rid)
            names[rid] = resource.name if resource else rid
            cap = float(getattr(resource, "capacity_percent", 100.0) or 100.0) if resource else 100.0
            if cap <= 0.0:
                cap = 100.0
            self._resource_threshold_by_id[rid] = cap * scale
        return names

    def _priority_value(self, task: Task) -> int:
        from src.core.modules.project_management.application.scheduling.utils.task_priority import get_task_priority_value
        return get_task_priority_value(task)


__all__ = ["ResourceLevelingEngine"]
