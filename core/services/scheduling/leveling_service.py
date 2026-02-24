from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.interfaces import AssignmentRepository, DependencyRepository, ResourceRepository, TaskRepository
from core.models import Task, TaskAssignment
from core.services.scheduling.leveling import (
    build_resource_conflicts,
    build_successors_map,
    choose_auto_level_task,
)
from core.services.scheduling.leveling_models import (
    ResourceConflict,
    ResourceLevelingAction,
    ResourceLevelingResult,
)
from core.services.work_calendar.engine import WorkCalendarEngine


class ResourceLevelingMixin:
    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    _assignment_repo: AssignmentRepository | None
    _resource_repo: ResourceRepository | None
    _calendar: WorkCalendarEngine

    def preview_resource_conflicts(
        self,
        project_id: str,
        threshold_percent: float = 100.0,
    ) -> list[ResourceConflict]:
        if threshold_percent <= 0:
            raise ValidationError(
                "threshold_percent must be greater than zero.",
                code="RESOURCE_LEVELING_INVALID_THRESHOLD",
            )

        tasks = self._task_repo.list_by_project(project_id)
        if not tasks:
            return []

        assignments = self._list_project_assignments(tasks)
        if not assignments:
            return []

        tasks_by_id = {task.id: task for task in tasks}
        resource_names = self._build_resource_name_map(assignments)
        return build_resource_conflicts(
            tasks_by_id=tasks_by_id,
            assignments=assignments,
            calendar=self._calendar,
            resource_name_by_id=resource_names,
            threshold_percent=threshold_percent,
        )

    def resolve_resource_conflict_manual(
        self,
        project_id: str,
        task_id: str,
        shift_working_days: int = 1,
        reason: str = "Manual resource leveling",
    ) -> ResourceLevelingAction:
        if shift_working_days <= 0:
            raise ValidationError(
                "shift_working_days must be positive.",
                code="RESOURCE_LEVELING_INVALID_SHIFT",
            )

        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise ValidationError(
                "Task does not belong to the selected project.",
                code="RESOURCE_LEVELING_PROJECT_MISMATCH",
            )
        if task.start_date is None:
            raise ValidationError(
                "Task must have a start date for leveling.",
                code="RESOURCE_LEVELING_NO_START",
            )
        if getattr(task, "actual_start", None) is not None or getattr(task, "actual_end", None) is not None:
            raise BusinessRuleError(
                "Cannot shift a task that already has actual dates.",
                code="RESOURCE_LEVELING_LOCKED_TASK",
            )

        successors = build_successors_map(self._dependency_repo.list_by_project(project_id))
        if successors.get(task.id):
            raise BusinessRuleError(
                "Manual leveling supports only tasks without successors.",
                code="RESOURCE_LEVELING_DEPENDENCY_BLOCK",
            )

        action = self._shift_task_for_leveling(
            task=task,
            shift_working_days=shift_working_days,
            reason=reason,
            resource_id=None,
            resource_name=None,
            conflict_date=None,
        )
        try:
            self._task_repo.update(task)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return action

    def auto_level_resources(
        self,
        project_id: str,
        max_iterations: int = 60,
        threshold_percent: float = 100.0,
    ) -> ResourceLevelingResult:
        if max_iterations <= 0:
            raise ValidationError(
                "max_iterations must be positive.",
                code="RESOURCE_LEVELING_INVALID_ITERATIONS",
            )

        initial_conflicts = self.preview_resource_conflicts(
            project_id=project_id,
            threshold_percent=threshold_percent,
        )
        actions: list[ResourceLevelingAction] = []
        successors = build_successors_map(self._dependency_repo.list_by_project(project_id))
        iterations = 0

        while iterations < max_iterations:
            tasks = self._task_repo.list_by_project(project_id)
            if not tasks:
                break
            assignments = self._list_project_assignments(tasks)
            if not assignments:
                break

            tasks_by_id = {task.id: task for task in tasks}
            resource_names = self._build_resource_name_map(assignments)
            conflicts = build_resource_conflicts(
                tasks_by_id=tasks_by_id,
                assignments=assignments,
                calendar=self._calendar,
                resource_name_by_id=resource_names,
                threshold_percent=threshold_percent,
            )
            if not conflicts:
                break

            top_conflict = max(
                conflicts,
                key=lambda c: (c.total_allocation_percent, len(c.entries)),
            )
            task_id = choose_auto_level_task(
                conflict=top_conflict,
                tasks_by_id=tasks_by_id,
                successors_by_task_id=successors,
                priority_value=self._priority_value,
            )
            if task_id is None:
                break

            task = tasks_by_id[task_id]
            action = self._shift_task_for_leveling(
                task=task,
                shift_working_days=1,
                reason=(
                    "Auto-leveling: resolved "
                    f"{top_conflict.total_allocation_percent:.1f}% load on "
                    f"{top_conflict.conflict_date.isoformat()}"
                ),
                resource_id=top_conflict.resource_id,
                resource_name=top_conflict.resource_name,
                conflict_date=top_conflict.conflict_date,
            )
            try:
                self._task_repo.update(task)
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise

            actions.append(action)
            iterations += 1

        final_conflicts = self.preview_resource_conflicts(
            project_id=project_id,
            threshold_percent=threshold_percent,
        )
        return ResourceLevelingResult(
            conflicts_before=len(initial_conflicts),
            conflicts_after=len(final_conflicts),
            iterations=iterations,
            actions=actions,
        )

    def _list_project_assignments(self, tasks: list[Task]) -> list[TaskAssignment]:
        if self._assignment_repo is None:
            raise BusinessRuleError(
                "Scheduling engine is missing assignment repository for resource leveling.",
                code="RESOURCE_LEVELING_UNAVAILABLE",
            )
        task_ids = [task.id for task in tasks]
        if not task_ids:
            return []
        return self._assignment_repo.list_by_tasks(task_ids)

    def _build_resource_name_map(
        self,
        assignments: list[TaskAssignment],
    ) -> dict[str, str]:
        names: dict[str, str] = {}
        if self._resource_repo is None:
            for assignment in assignments:
                names.setdefault(assignment.resource_id, assignment.resource_id)
            return names
        for assignment in assignments:
            rid = assignment.resource_id
            if rid in names:
                continue
            resource = self._resource_repo.get(rid)
            names[rid] = resource.name if resource else rid
        return names

    def _shift_task_for_leveling(
        self,
        task: Task,
        shift_working_days: int,
        reason: str,
        resource_id: str | None,
        resource_name: str | None,
        conflict_date: date | None,
    ) -> ResourceLevelingAction:
        old_start = task.start_date
        old_end = task.end_date

        if old_start is None:
            raise ValidationError(
                "Task must have a start date for leveling.",
                code="RESOURCE_LEVELING_NO_START",
            )

        # add_working_days is inclusive (1 returns same day), so +1 to shift by N days.
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
