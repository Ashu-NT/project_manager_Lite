from __future__ import annotations

from src.core.modules.project_management.domain.projects.project import ProjectResource
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


class TaskAssignmentBridgeMixin:
    def assign_resource(
        self, task_id: str, resource_id: str, allocation_percent: float = 100.0
    ) -> TaskAssignment:
        """Convenience entry point: resolves (or auto-provisions) the
        resource's ProjectResource envelope on this task's project, then
        delegates to assign_project_resource -- the same membership
        invariant (a TaskAssignment always has a real, active ProjectResource
        behind it) applies here as it does to the primary entry point;
        there is no bypass for a repository-not-configured case, since a
        real TaskService always has one wired (see docs §43/§80)."""
        self._require_manage("add assignment")
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        self._require_manage("add assignment", project_id=task.project_id)
        self._require_leaf_task(task, operation_label="receive resource assignments")

        if not self._project_resource_repo:
            raise BusinessRuleError(
                "Project resource repository is not configured.",
                code="PROJECT_RESOURCE_REPO_MISSING",
            )

        resource = self._resource_repo.get(resource_id)
        if not resource:
            raise NotFoundError("Resource not found.", code="RESOURCE_NOT_FOUND")
        assignment = TaskAssignment.create(task_id, resource_id, allocation_percent)

        project_resource = self._project_resource_repo.get_for_project(task.project_id, resource_id)
        if not project_resource:
            project_resource = ProjectResource.create(
                project_id=task.project_id,
                resource_id=resource_id,
                hourly_rate=getattr(resource, "hourly_rate", None),
                currency_code=getattr(resource, "currency_code", None),
                planned_hours=0.0,
                is_active=bool(getattr(resource, "is_active", True)),
            )
            try:
                self._project_resource_repo.add(project_resource)
                self._session.commit()
            except Exception:
                self._session.rollback()
                raise

        return self.assign_project_resource(
            task_id=task_id,
            project_resource_id=project_resource.id,
            allocation_percent=assignment.allocation_percent,
        )


__all__ = ["TaskAssignmentBridgeMixin"]
