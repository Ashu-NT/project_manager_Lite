# core/services/cost_service.py
from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from datetime import date
from core.models import CostItem, CostType
from core.interfaces import CostRepository, ProjectRepository, TaskRepository
from core.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.events.domain_events import domain_events
from core.services.approval.policy import is_governance_required
from core.services.audit.helpers import record_audit
from core.services.auth.authorization import require_permission

DEFAULT_CURRENCY_CODE = "EUR"


class CostService:
    def __init__(
        self,
        session: Session,
        cost_repo: CostRepository,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        user_session=None,
        audit_service=None,
        approval_service=None,
    ):
        self._session: Session = session
        self._cost_repo: CostRepository = cost_repo
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._user_session = user_session
        self._audit_service = audit_service
        self._approval_service = approval_service

    def add_cost_item(
        self,
        project_id: str,
        description: str,
        planned_amount: float,
        task_id: str | None = None,
        cost_type: CostType = CostType.OVERHEAD,
        committed_amount: float = 0.0,
        actual_amount: float = 0.0,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        bypass_approval: bool = False,
    ) -> CostItem:
        require_permission(self._user_session, "cost.manage", operation_label="add cost item")
        if not isinstance(cost_type, CostType):
            cost_type = CostType(str(cost_type))
        if not self._project_repo.get(project_id):
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        if task_id is not None:
            task = self._task_repo.get(task_id)
            if not task:
                raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
            if task.project_id != project_id:
                raise ValidationError(
                    "Task must belong to the selected project.",
                    code="TASK_PROJECT_MISMATCH",
                )

        if planned_amount < 0:
            raise ValidationError("Planned amount cannot be negative.")
        
        if committed_amount < 0:
            raise ValidationError("Committed amount cannot be negative.")   
        
        if actual_amount < 0:
            raise ValidationError("Actual amount cannot be negative.")
        
        if incurred_date is not None and not isinstance(incurred_date, date):
            raise ValidationError("Incurred date must be a valid date.")
        resolved_currency = (currency_code or "").strip().upper() or DEFAULT_CURRENCY_CODE
        if (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required("cost.add")
        ):
            req = self._approval_service.request_change(
                request_type="cost.add",
                entity_type="cost_item",
                entity_id=task_id or project_id,
                project_id=project_id,
                payload={
                    "project_id": project_id,
                    "task_id": task_id,
                    "description": description,
                    "planned_amount": planned_amount,
                    "committed_amount": committed_amount,
                    "actual_amount": actual_amount,
                    "cost_type": cost_type.value,
                    "incurred_date": str(incurred_date) if incurred_date else None,
                    "currency_code": resolved_currency,
                },
            )
            raise BusinessRuleError(
                f"Approval required for cost creation. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )

        cost_item = CostItem.create(
            project_id=project_id,
            task_id=task_id,
            description=description.strip(),
            planned_amount=planned_amount,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            cost_type=cost_type,
            incurred_date=incurred_date,
            currency_code=resolved_currency,
        )

        try:
            self._cost_repo.add(cost_item)
            self._session.commit()
            record_audit(
                self,
                action="cost.add",
                entity_type="cost_item",
                entity_id=cost_item.id,
                project_id=project_id,
                details={
                    "description": cost_item.description,
                    "planned_amount": cost_item.planned_amount,
                    "actual_amount": cost_item.actual_amount,
                },
            )
        except Exception as e:
            self._session.rollback()
            raise e
        
        domain_events.costs_changed.emit(project_id)
        return cost_item

    def update_cost_item(
        self,
        cost_id: str,
        description: str | None = None,
        planned_amount: float | None = None,
        committed_amount: float| None = None,
        actual_amount: float | None = None,
        cost_type : CostType | None = None,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        expected_version: int | None = None,
        bypass_approval: bool = False,
    ) -> CostItem:
        require_permission(self._user_session, "cost.manage", operation_label="update cost item")
        item = self._cost_repo.get(cost_id)
        if not item:
            raise NotFoundError("Cost item not found.", code="COST_NOT_FOUND")
        if expected_version is not None and item.version != expected_version:
            raise ConcurrencyError(
                "Cost item changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        if (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required("cost.update")
        ):
            req = self._approval_service.request_change(
                request_type="cost.update",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                payload={
                    "cost_id": cost_id,
                    "description": description,
                    "planned_amount": planned_amount,
                    "committed_amount": committed_amount,
                    "actual_amount": actual_amount,
                    "cost_type": cost_type.value if cost_type else None,
                    "incurred_date": str(incurred_date) if incurred_date else None,
                    "currency_code": currency_code,
                    "expected_version": expected_version,
                },
            )
            raise BusinessRuleError(
                f"Approval required for cost update. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )

        if description is not None:
            item.description = description.strip()
            
        if planned_amount is not None:
            if planned_amount < 0:
                raise ValidationError("Planned amount cannot be negative.")
            item.planned_amount = planned_amount
            
        if actual_amount is not None:
            if actual_amount < 0:
                raise ValidationError("Actual amount cannot be negative.")
            item.actual_amount = actual_amount
            
        if committed_amount is not None:
            if committed_amount < 0:
                raise ValidationError("Committed amount cannot be negative.")
            item.committed_amount = committed_amount
        
        if cost_type is not None:
            if not isinstance(cost_type, CostType):
                cost_type = CostType(str(cost_type))
            item.cost_type = cost_type
        
        if incurred_date is not None:
            if not isinstance(incurred_date, date):
                raise ValidationError("Incurred date must be a valid date.")
            item.incurred_date = incurred_date
        
        if currency_code is not None:
            item.currency_code = currency_code.strip().upper() or DEFAULT_CURRENCY_CODE
        

        try:
            self._cost_repo.update(item)
            self._session.commit()
            record_audit(
                self,
                action="cost.update",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                details={
                    "description": item.description,
                    "planned_amount": item.planned_amount,
                    "actual_amount": item.actual_amount,
                },
            )
        except Exception as e:
            self._session.rollback()
            raise e
        
        domain_events.costs_changed.emit(item.project_id)
        return item

    def delete_cost_item(self, cost_id: str, bypass_approval: bool = False) -> None:
        require_permission(self._user_session, "cost.manage", operation_label="delete cost item")
        item = self._cost_repo.get(cost_id)
        if not item:
            raise NotFoundError("Cost item not found.", code="COST_NOT_FOUND")
        if (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required("cost.delete")
        ):
            req = self._approval_service.request_change(
                request_type="cost.delete",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                payload={"cost_id": cost_id},
            )
            raise BusinessRuleError(
                f"Approval required for cost deletion. Request {req.id} created.",
                code="APPROVAL_REQUIRED",
            )
        try:
            self._cost_repo.delete(cost_id)
            self._session.commit()
            record_audit(
                self,
                action="cost.delete",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                details={"description": item.description},
            )
        except Exception as e:
            self._session.rollback()
            raise e
        
        domain_events.costs_changed.emit(item.project_id)

    def list_cost_items_for_project(self, project_id: str) -> List[CostItem]:
        return self._cost_repo.list_by_project(project_id)

    def get_project_cost_summary(self, project_id: str) -> dict:
        if not self._project_repo.get(project_id):
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        items = self._cost_repo.list_by_project(project_id)
        total_planned = sum(i.planned_amount for i in items)
        total_committed = sum(i.committed_amount for i in items)
        total_actual = sum(i.actual_amount for i in items)
        variance = total_actual - total_planned
        committed_variance = total_committed - total_planned

        # Keep both legacy and normalized keys for backwards compatibility.
        return {
            "project_id": project_id,
            "total_planned": total_planned,
            "total_committed": total_committed,
            "total-committed": total_committed,
            "total_actual": total_actual,
            "variance": variance,
            "variance_actual": variance,
            "variance_commitment": committed_variance,
            "variance_committment": committed_variance,
            "exposure": total_committed + total_actual,
            "items_count": len(items),
        }


