from __future__ import annotations

from typing import TYPE_CHECKING

from src.core.modules.project_management.domain.tasks.task import TaskDependency
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.approval.policy import is_governance_required
from src.core.shared.activity import record_activity
from src.core.platform.auth.authorization import is_admin_session, require_permission
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.modules.project_management.domain.enums import DependencyType

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.core.modules.project_management.contracts.repositories.task import (
        DependencyRepository,
        TaskRepository,
    )


class TaskDependencyMixin:
    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository
    def get_dependency(self, dep_id: str) -> TaskDependency | None:
        require_permission(self._user_session, "task.read", operation_label="view dependency")
        dependency = self._dependency_repo.get(dep_id)
        if dependency is None:
            return None
        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "task.read",
                operation_label="view dependency",
            )
        return dependency

    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
        bypass_approval: bool = False,
    ) -> TaskDependency:
        predecessor = self._task_repo.get(predecessor_id)
        if not predecessor:
            raise NotFoundError("Predecessor task not found", code="TASK_NOT_FOUND")
        successor = self._task_repo.get(successor_id)
        if not successor:
            raise NotFoundError("Successor task not found", code="TASK_NOT_FOUND")
        governed = (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required("dependency.add")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency change")
            require_project_permission(
                self._user_session,
                predecessor.project_id,
                "approval.request",
                operation_label="request dependency change",
            )
        else:
            require_permission(self._user_session, "task.manage", operation_label="add dependency")
            require_project_permission(
                self._user_session,
                predecessor.project_id,
                "task.manage",
                operation_label="add dependency",
            )
        diagnostic = self.get_dependency_diagnostics(
            predecessor_id=predecessor_id,
            successor_id=successor_id,
            dependency_type=dependency_type,
            lag_days=lag_days,
            include_impact=False,
        )
        if not diagnostic.is_valid:
            message = diagnostic.summary
            if diagnostic.detail:
                message = f"{diagnostic.summary}\n{diagnostic.detail}"
            if diagnostic.code == "TASK_NOT_FOUND":
                raise NotFoundError(message, code=diagnostic.code)
            if diagnostic.code == "DEPENDENCY_CYCLE":
                raise BusinessRuleError(message, code=diagnostic.code)
            raise ValidationError(message, code=diagnostic.code)
        if governed:
            request = self._approval_service.request_change(
                request_type="dependency.add",
                entity_type="task_dependency",
                entity_id=successor_id,
                project_id=predecessor.project_id,
                payload={
                    "predecessor_id": predecessor_id,
                    "predecessor_name": predecessor.name,
                    "successor_id": successor_id,
                    "successor_name": successor.name,
                    "dependency_type": dependency_type.value,
                    "lag_days": lag_days,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency change. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )
        dependency = TaskDependency.create(predecessor_id, successor_id, dependency_type, lag_days)
        try:
            self._dependency_repo.add(dependency)
            self._session.commit()
            self._sync_project_schedule(predecessor.project_id)
            record_activity(
                self,
                action="dependency.add",
                entity_type="task_dependency",
                entity_id=dependency.id,
                module="project_management",
                workspace_id=predecessor.project_id,
                details={
                    "predecessor_name": predecessor.name,
                    "successor_name": successor.name,
                    "type": dependency.dependency_type.value,
                    "lag_days": dependency.lag_days,
                },
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(predecessor.project_id)
        return dependency

    def remove_dependency(self, dep_id: str, bypass_approval: bool = False) -> None:
        governed = (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required("dependency.remove")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency removal")
        else:
            require_permission(self._user_session, "task.manage", operation_label="remove dependency")
        dependency = self._dependency_repo.get(dep_id)
        if not dependency:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "approval.request" if governed else "task.manage",
                operation_label="request dependency removal" if governed else "remove dependency",
            )
        if governed:
            request = self._approval_service.request_change(
                request_type="dependency.remove",
                entity_type="task_dependency",
                entity_id=dependency.id,
                project_id=project_id,
                payload={
                    "dependency_id": dependency.id,
                    "predecessor_id": dependency.predecessor_task_id,
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_id": dependency.successor_task_id,
                    "successor_name": successor.name if successor else None,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency removal. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )
        try:
            self._dependency_repo.delete(dep_id)
            self._session.commit()
            project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
            self._sync_project_schedule(project_id)
            record_activity(
                self,
                action="dependency.remove",
                entity_type="task_dependency",
                entity_id=dep_id,
                module="project_management",
                workspace_id=project_id,
                details={
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_name": successor.name if successor else None,
                },
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        if project_id:
            domain_events.tasks_changed.emit(project_id)

    def list_dependencies_for_task(self, task_id: str) -> list[TaskDependency]:
        require_permission(self._user_session, "task.read", operation_label="list task dependencies")
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        require_project_permission(
            self._user_session,
            task.project_id,
            "task.read",
            operation_label="list task dependencies",
        )
        return self._dependency_repo.list_by_task(task_id)

    def update_dependency(
        self,
        dep_id: str,
        *,
        dependency_type: DependencyType | None = None,
        lag_days: int | None = None,
        bypass_approval: bool = False,
    ) -> TaskDependency:
        dependency = self._dependency_repo.get(dep_id)
        if not dependency:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")

        predecessor = self._task_repo.get(dependency.predecessor_task_id)
        successor = self._task_repo.get(dependency.successor_task_id)
        project_id = predecessor.project_id if predecessor else (successor.project_id if successor else None)
        governed = (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required("dependency.update")
            and not is_admin_session(self._user_session)
        )
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency update")
        else:
            require_permission(self._user_session, "task.manage", operation_label="update dependency")
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "approval.request" if governed else "task.manage",
                operation_label="request dependency update" if governed else "update dependency",
            )

        next_dependency_type = dependency_type or dependency.dependency_type
        next_lag_days = int(dependency.lag_days if lag_days is None else lag_days)
        diagnostic = self.get_dependency_diagnostics(
            predecessor_id=dependency.predecessor_task_id,
            successor_id=dependency.successor_task_id,
            dependency_type=next_dependency_type,
            lag_days=next_lag_days,
            include_impact=False,
        )
        if not diagnostic.is_valid and diagnostic.code not in {"DEPENDENCY_DUPLICATE"}:
            message = diagnostic.summary
            if diagnostic.detail:
                message = f"{diagnostic.summary}\n{diagnostic.detail}"
            if diagnostic.code == "DEPENDENCY_CYCLE":
                raise BusinessRuleError(message, code=diagnostic.code)
            raise ValidationError(message, code=diagnostic.code)

        if governed:
            request = self._approval_service.request_change(
                request_type="dependency.update",
                entity_type="task_dependency",
                entity_id=dependency.id,
                project_id=project_id,
                payload={
                    "dependency_id": dependency.id,
                    "predecessor_id": dependency.predecessor_task_id,
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_id": dependency.successor_task_id,
                    "successor_name": successor.name if successor else None,
                    "dependency_type": next_dependency_type.value,
                    "lag_days": next_lag_days,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency update. Request {request.id} created.",
                code="APPROVAL_REQUIRED",
            )

        dependency.dependency_type = next_dependency_type
        dependency.lag_days = next_lag_days
        try:
            self._dependency_repo.update(dependency)
            self._session.commit()
            if project_id:
                self._sync_project_schedule(project_id)
            record_activity(
                self,
                action="dependency.update",
                entity_type="task_dependency",
                entity_id=dependency.id,
                module="project_management",
                workspace_id=project_id,
                details={
                    "predecessor_name": predecessor.name if predecessor else None,
                    "successor_name": successor.name if successor else None,
                    "type": dependency.dependency_type.value,
                    "lag_days": dependency.lag_days,
                },
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        if project_id:
            domain_events.tasks_changed.emit(project_id)
        return dependency


__all__ = ["TaskDependencyMixin"]
