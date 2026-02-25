from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from core.events.domain_events import domain_events
from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.interfaces import DependencyRepository, TaskRepository
from core.models import DependencyType, TaskDependency
from core.services.approval.policy import is_governance_required
from core.services.audit.helpers import record_audit
from core.services.auth.authorization import require_permission
class TaskDependencyMixin:
    _session: Session
    _task_repo: TaskRepository
    _dependency_repo: DependencyRepository

    def add_dependency(
        self,
        predecessor_id: str,
        successor_id: str,
        dependency_type: DependencyType = DependencyType.FINISH_TO_START,
        lag_days: int = 0,
        bypass_approval: bool = False,
    ) -> TaskDependency:
        governed = (not bypass_approval and self._approval_service is not None and is_governance_required("dependency.add"))
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency change")
        else:
            require_permission(self._user_session, "task.manage", operation_label="add dependency")
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

        pred = self._task_repo.get(predecessor_id)
        if not pred:
            raise NotFoundError("Predecessor task not found", code="TASK_NOT_FOUND")
        if governed:
            req = self._approval_service.request_change(
                request_type="dependency.add",
                entity_type="task_dependency",
                entity_id=successor_id,
                project_id=pred.project_id,
                payload={
                    "predecessor_id": predecessor_id,
                    "successor_id": successor_id,
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
            record_audit(
                self,
                action="dependency.add",
                entity_type="task_dependency",
                entity_id=dep.id,
                project_id=pred.project_id,
                details={
                    "predecessor_id": dep.predecessor_task_id,
                    "successor_id": dep.successor_task_id,
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
        governed = (not bypass_approval and self._approval_service is not None and is_governance_required("dependency.remove"))
        if governed:
            require_permission(self._user_session, "approval.request", operation_label="request dependency removal")
        else:
            require_permission(self._user_session, "task.manage", operation_label="remove dependency")
        dep = self._dependency_repo.get(dep_id)
        if not dep:
            raise NotFoundError("Dependency not found.", code="DEPENDENCY_NOT_FOUND")
        pred = self._task_repo.get(dep.predecessor_task_id)
        succ = self._task_repo.get(dep.successor_task_id)
        if governed:
            project_id = pred.project_id if pred else (succ.project_id if succ else None)
            req = self._approval_service.request_change(
                request_type="dependency.remove",
                entity_type="task_dependency",
                entity_id=dep.id,
                project_id=project_id,
                payload={"dependency_id": dep.id},
            )
            raise BusinessRuleError(
                f"Approval required for dependency removal. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )
        try:
            self._dependency_repo.delete(dep_id)
            self._session.commit()
            project_id = pred.project_id if pred else (succ.project_id if succ else None)
            record_audit(
                self,
                action="dependency.remove",
                entity_type="task_dependency",
                entity_id=dep_id,
                project_id=project_id,
                details={
                    "predecessor_id": dep.predecessor_task_id,
                    "successor_id": dep.successor_task_id,
                },
            )
        except Exception as exc:
            self._session.rollback()
            raise exc
        project_id = pred.project_id if pred else (succ.project_id if succ else None)
        if project_id:
            domain_events.tasks_changed.emit(project_id)

    def list_dependencies_for_task(self, task_id: str) -> List[TaskDependency]:
        return self._dependency_repo.list_by_task(task_id)
