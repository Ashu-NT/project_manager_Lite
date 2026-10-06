from __future__ import annotations

from datetime import datetime, timezone

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.projects.commands.support import (
    ProjectSupportMixin,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectRemoved,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskRemoved,
)
from src.core.modules.project_management.domain.tasks.hierarchy import (
    order_tasks_children_first,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    NotFoundError,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class ProjectDeletionMixin(ProjectSupportMixin):
    def delete_project(self, project_id: str) -> None:
        require_permission(self._user_session, "project.manage", operation_label="delete project")
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found")
        require_project_permission(
            self._user_session,
            project.id,
            "project.manage",
            operation_label="delete project",
        )
        scope = self._require_project_scope_ids(operation_label="delete project")

        with self._require_shared_uow_factory().create(context=self._new_context()) as uow:
            tasks = order_tasks_children_first(self._task_repo.list_by_project(project_id))
            for task in tasks:
                self._dependency_repo.delete_for_task(task.id)
                assignments = self._assignment_repo.list_by_task(task.id)
                if self._time_entry_repo is not None:
                    for assignment in assignments:
                        self._time_entry_repo.delete_by_assignment(assignment.id)
                    self._session.flush()
                self._assignment_repo.delete_by_task(task.id)
                self._task_repo.delete_with_version_check(task.id, expected_version=task.version)
                # One TaskRemoved per deleted Task, same transaction as the Project
                # delete -- Task is an independently versioned/audited aggregate, so
                # its removal is its own fact, never a synthetic bulk fact.
                uow.record_event(
                    TaskRemoved(
                        tenant_id=scope.tenant_id,
                        organization_id=scope.organization_id,
                        project_id=project_id,
                        task_id=task.id,
                        occurred_at=datetime.now(timezone.utc),
                    )
                )

            self._project_repo.delete(project_id)
            record_audit_entry(
                self,
                operation="delete",
                entity_type="project",
                entity_id=project.id,
                module="project_management",
                organization_id=scope.organization_id,
                category="MASTER_DATA",
                severity="medium",
                before_data={"name": project.name, "status": project.status.value},
                workspace_id=project.id,
                metadata={"action": "project.delete"},
                commit=False,
                fail_closed=True,
            )
            record_activity(
                self,
                action="project.delete",
                entity_type="project",
                entity_id=project.id,
                module="project_management",
                workspace_id=project.id,
                message=f"Deleted project {project.name}",
                details={"name": project.name},
                commit=False,
            )
            uow.record_event(
                ProjectRemoved(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=project.id,
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            uow.commit()
