from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.resources.task_assignment_capacity_service import (
    CAPACITY_OVER_CAPACITY,
    evaluate_task_assignment_capacity,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


class TaskValidationMixin:
    _task_repo: TaskRepository
    _assignment_repo: AssignmentRepository
    _resource_repo: ResourceRepository | None
    _project_repo: ProjectRepository | None
    _overallocation_policy: str
    _last_overallocation_warning: str | None

    def _validate_task_within_project_dates(
        self, project_id: str, task_start: date | None, task_end: date | None
    ):
        if self._project_repo is None:
            return
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        project_start = getattr(project, "start_date", None)
        project_end = getattr(project, "end_date", None)

        if project_start and task_start and task_start < project_start:
            raise ValidationError(
                f"Task start date ({task_start}) can not be before project start ({project_start})",
                code="TASK_INVALID_DATE",
            )
        if project_end and task_start and task_start > project_end:
            raise ValidationError(
                f"Task start date ({task_start}) can not be after project end ({project_end})",
                code="TASK_INVALID_DATE",
            )
        if project_start and task_end and task_end < project_start:
            raise ValidationError(
                f"Task end date ({task_end}) can not be before project start ({project_start})",
                code="TASK_INVALID_DATE",
            )
        if project_end and task_end and task_end > project_end:
            raise ValidationError(
                f"Task end date ({task_end}) can not be after project end ({project_end})",
                code="TASK_INVALID_DATE",
            )


    def _check_resource_overallocation(
        self,
        project_id: str,
        resource_id: str,
        new_task_id: str,
        new_alloc_percent: float,
        exclude_assignment_id: str | None = None,
    ) -> str | None:
        """Authoritative calendar-based capacity check (docs §44). Delegates
        the actual capacity calculation to
        ``evaluate_task_assignment_capacity`` -- the enterprise calendar
        resolver, `Resource.capacity_percent`, and real per-day
        assignment commitments, not a naive Mon-Fri model. Falls back to
        skipping the check (never to the old duplicate arithmetic) when the
        authoritative service isn't configured, e.g. in lightweight test
        construction that doesn't wire every optional dependency."""
        self._last_overallocation_warning = None
        new_task = self._task_repo.get(new_task_id)
        if not new_task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        new_start = getattr(new_task, "start_date", None)
        new_end = getattr(new_task, "end_date", None)
        if not new_start or not new_end:
            return None

        availability_service = getattr(self, "_enterprise_resource_availability_service", None)
        if availability_service is None:
            return None

        fact = evaluate_task_assignment_capacity(
            resource_id=resource_id,
            project_id=project_id,
            start_date=new_start,
            end_date=new_end,
            proposed_allocation_percent=float(new_alloc_percent or 0.0),
            task_repo=self._task_repo,
            assignment_repo=self._assignment_repo,
            resource_repo=getattr(self, "_resource_repo", None),
            availability_service=availability_service,
            exclude_assignment_id=exclude_assignment_id,
        )

        if fact.capacity_status != CAPACITY_OVER_CAPACITY:
            return None

        conflict_task_ids: set[str] = set()
        for day in fact.days:
            if day.status == CAPACITY_OVER_CAPACITY:
                conflict_task_ids.update(day.contributing_task_ids)
        task_names = []
        for task_id in list(conflict_task_ids)[:6]:
            task = self._task_repo.get(task_id)
            if task is not None:
                task_names.append(getattr(task, "name", task_id))
        task_names.append(getattr(new_task, "name", new_task_id))
        extra = "..." if len(conflict_task_ids) > 6 else ""
        conflict_dates_label = ", ".join(d.isoformat() for d in fact.conflict_dates[:6])
        if len(fact.conflict_dates) > 6:
            conflict_dates_label += ", ..."
        message = (
            f"Resource would be over-allocated on {conflict_dates_label} "
            f"(peak {fact.peak_utilization_percent:.1f}% of effective capacity).\n"
            f"Tasks: {', '.join(task_names)}{extra}"
        )
        if getattr(self, "_overallocation_policy", "warn") == "strict":
            raise BusinessRuleError(message, code="RESOURCE_OVERALLOCATED")
        self._last_overallocation_warning = message
        return message


__all__ = ["TaskValidationMixin"]
