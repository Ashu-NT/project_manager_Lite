from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.access.scope_permissions import (
    require_any_project_permission,
    require_project_permission,
)
from src.core.modules.project_management.application.common import (
    project_resource_envelope_policy as envelope_policy,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectResourceUsageFact,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class ProjectResourceQueryMixin:
    _project_resource_repo: ProjectResourceRepository
    _resource_repo: ResourceRepository
    _task_repo: TaskRepository | None
    _assignment_repo: AssignmentRepository | None

    def list_by_project(self, project_id: str) -> list[ProjectResource]:
        require_permission(
            self._user_session,
            "project.read",
            operation_label="list project resources",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="list project resources",
        )
        return self._project_resource_repo.list_by_project(project_id)

    def list_for_project_workspace(self, project_id: str) -> list[ProjectResource]:
        require_any_project_permission(
            self._user_session,
            project_id,
            ("project.read", "project.manage"),
            operation_label="list project resources",
        )
        return self._project_resource_repo.list_by_project(project_id)

    def list_for_task_workspace(self, project_id: str) -> list[ProjectResource]:
        require_any_project_permission(
            self._user_session,
            project_id,
            ("project.read", "task.read", "task.manage"),
            operation_label="list task project resources",
        )
        return self._project_resource_repo.list_by_project(project_id)

    def get(self, project_resource_id: str) -> ProjectResource | None:
        require_permission(
            self._user_session,
            "project.read",
            operation_label="view project resource",
        )
        row = self._project_resource_repo.get(project_resource_id)
        if row is None:
            return None
        require_project_permission(
            self._user_session,
            row.project_id,
            "project.read",
            operation_label="view project resource",
        )
        return row

    def get_usage(self, project_resource_id: str) -> ProjectResourceUsageFact:
        """Authoritative planned/allocated/unallocated/actual/remaining
        reconciliation for one ProjectResource -- see docs §43/§80 for the
        semantics. Not derived from whatever page of tasks the caller
        happens to have loaded."""
        require_permission(
            self._user_session,
            "project.read",
            operation_label="view project resource usage",
        )
        project_resource = self._project_resource_repo.get(project_resource_id)
        if project_resource is None:
            raise NotFoundError(
                "Project resource not found.", code="PROJECT_RESOURCE_NOT_FOUND"
            )
        require_project_permission(
            self._user_session,
            project_resource.project_id,
            "project.read",
            operation_label="view project resource usage",
        )

        planned_hours = project_resource.planned_hours
        if self._task_repo is None or self._assignment_repo is None:
            allocated_total = actual_total = None
            task_assignment_count = 0
        else:
            assignments = envelope_policy.resource_assignments_in_project(
                task_repo=self._task_repo,
                assignment_repo=self._assignment_repo,
                project_id=project_resource.project_id,
                resource_id=project_resource.resource_id,
            )
            task_assignment_count = len(assignments)
            allocated_total = sum(
                (a.allocated_planned_hours for a in assignments), Decimal("0")
            )
            actual_total = sum((a.hours_logged for a in assignments), Decimal("0"))

        allocated_total = allocated_total if allocated_total is not None else Decimal("0")
        actual_total = actual_total if actual_total is not None else Decimal("0")
        unallocated = planned_hours - allocated_total
        remaining = planned_hours - actual_total

        return ProjectResourceUsageFact(
            project_resource_id=project_resource.id,
            project_id=project_resource.project_id,
            resource_id=project_resource.resource_id,
            planned_hours=planned_hours,
            allocated_to_tasks_hours=allocated_total,
            unallocated_planned_hours=unallocated,
            actual_hours=actual_total,
            remaining_project_hours=remaining,
            planned_burn_percent=envelope_policy.planned_burn_percent(
                planned_hours=planned_hours, actual_hours=actual_total
            ),
            task_assignment_count=task_assignment_count,
            envelope_status=envelope_policy.envelope_status(
                planned_hours=planned_hours, allocated_total=allocated_total
            ),
            burn_status=envelope_policy.burn_status(
                planned_hours=planned_hours, actual_hours=actual_total
            ),
            version=project_resource.version,
        )

    def get_for_project(self, project_id: str, resource_id: str) -> ProjectResource | None:
        require_permission(
            self._user_session,
            "project.read",
            operation_label="view project resource membership",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "project.read",
            operation_label="view project resource membership",
        )
        return self._project_resource_repo.get_for_project(project_id, resource_id)


__all__ = ["ProjectResourceQueryMixin"]
