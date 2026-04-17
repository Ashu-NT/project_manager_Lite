from __future__ import annotations
from typing import List
from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.modules.project_management.domain.enums import DependencyType
from core.modules.project_management.domain.task import TaskDependency
from core.platform.approval.policy import is_governance_required
from src.core.platform.access.authorization import require_project_permission
from core.platform.audit.helpers import record_audit
from src.core.platform.auth.authorization import is_admin_session, require_permission
class TaskDependencyMixin:
    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
        bypass_approval: bool = False,
    ) -> TaskDependency:
        pred = self._task_repo.get(predecessor_id)
        if not pred:
            raise NotFoundError("Predecessor task not found", code="TASK_NOT_FOUND")
        succ = self._task_repo.get(successor_id)
        if not succ:
            raise NotFoundError("Successor task not found", code="TASK_NOT_FOUND")
        governed = (not bypass_approval and self._approval_service is not None and is_governance_required("dependency.add") and not is_admin_session(self._user_session))
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency change")
            require_project_permission(
                self._user_session,
                pred.project_id,
                "approval.request",
                operation_label="request dependency change",
            )
        else:
            require_permission(self._user_session, "task.manage", operation_label="add dependency")
            require_project_permission(
                self._user_session,
                pred.project_id,
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
            req = self._approval_service.request_change(
                request_type="dependency.add",
                entity_type="task_dependency",
                entity_id=successor_id,
                project_id=pred.project_id,
                payload={
                    "predecessor_id": predecessor_id,
                    "predecessor_name": pred.name,
                    "successor_id": successor_id,
                    "successor_name": succ.name,
                    "dependency_type": dependency_type.value,
                    "lag_days": lag_days,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency change. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )
        dep = TaskDependency.create(predecessor_id, successor_id, dependency_type, lag_days)
        try:
            self._dependency_repo.add(dep)
            self._session.commit()
            self._sync_project_schedule(pred.project_id)
            record_audit(
                self,
                action="dependency.add",
                entity_type="task_dependency",
                entity_id=dep.id,
                project_id=pred.project_id,
                details={
                    "predecessor_name": pred.name,
                    "successor_name": succ.name,
                    "type": dep.dependency_type.value,
                    "lag_days": dep.lag_days,
                },
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        domain_events.tasks_changed.emit(pred.project_id)
        return dep

    def remove_dependency(self, dep_id: str, bypass_approval: bool = False) -> None:
        governed = (not bypass_approval and self._approval_service is not None and is_governance_required("dependency.remove") and not is_admin_session(self._user_session))
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency removal")
        else:
            require_permission(self._user_session, "task.manage", operation_label="remove dependency")
        dep = self._dependency_repo.get(dep_id)
        if not dep:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        pred = self._task_repo.get(dep.predecessor_task_id)
        succ = self._task_repo.get(dep.successor_task_id)
        project_id = pred.project_id if pred else (succ.project_id if succ else None)
        if project_id:
            require_project_permission(
                self._user_session,
                project_id,
                "approval.request" if governed else "task.manage",
                operation_label="request dependency removal" if governed else "remove dependency",
            )
        if governed:
            req = self._approval_service.request_change(
                request_type="dependency.remove",
                entity_type="task_dependency",
                entity_id=dep.id,
                project_id=project_id,
                payload={
                    "dependency_id": dep.id,
                    "predecessor_id": dep.predecessor_task_id,
                    "predecessor_name": pred.name if pred else None,
                    "successor_id": dep.successor_task_id,
                    "successor_name": succ.name if succ else None,
                },
            )
            raise BusinessRuleError(
                f"Approval required for dependency removal. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )
        try:
            self._dependency_repo.delete(dep_id)
            self._session.commit()
            project_id = pred.project_id if pred else (succ.project_id if succ else None)
            self._sync_project_schedule(project_id)
            record_audit(
                self,
                action="dependency.remove",
                entity_type="task_dependency",
                entity_id=dep_id,
                project_id=project_id,
                details={
                    "predecessor_name": pred.name if pred else None,
                    "successor_name": succ.name if succ else None,
                },
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        project_id = pred.project_id if pred else (succ.project_id if succ else None)
        if project_id:
            domain_events.tasks_changed.emit(project_id)

    def list_dependencies_for_task(self, task_id: str) -> List[TaskDependency]:
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
