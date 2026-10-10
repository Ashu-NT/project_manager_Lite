from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.projects.project_events import (
    ProjectRemoved,
)
from src.core.modules.project_management.application.tasks.task_events import (
    TaskRemoved,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.domain.tasks.hierarchy import (
    order_tasks_children_first,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    ActiveScopeIds,
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.persistence.unit_of_work import UnitOfWorkFactory


class ProjectDeletionHandler:
    def __init__(
        self,
        *,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        time_entry_repo: TimeEntryRepository | None,
        shared_uow_factory: UnitOfWorkFactory,
        tenant_context_service: TenantContextService,
        user_session: UserSessionContext | None,
        activity_service: ActivityService | None,
        enterprise_audit_service: object | None,
    ) -> None:
        self._session = session
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._dependency_repo = dependency_repo
        self._assignment_repo = assignment_repo
        self._time_entry_repo = time_entry_repo
        self._shared_uow_factory = shared_uow_factory
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._activity_service = activity_service
        self._enterprise_audit_service = enterprise_audit_service

    def _require_shared_uow_factory(self) -> UnitOfWorkFactory:
        return self._shared_uow_factory

    def _require_project_scope_ids(self, *, operation_label: str) -> ActiveScopeIds:
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    @staticmethod
    def _new_context() -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id())
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
