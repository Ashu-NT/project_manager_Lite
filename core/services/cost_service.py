# core/services/cost_service.py
from __future__ import annotations
from typing import List
from sqlalchemy.orm import Session
from datetime import date
from ..models import CostItem, CostType
from ..interfaces import CostRepository, ProjectRepository, TaskRepository
from ..exceptions import NotFoundError, ValidationError
from core.events.domain_events import domain_events

class CostService:
    def __init__(
        self,
        session: Session,
        cost_repo: CostRepository,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
    ):
        self._session = session
        self._cost_repo = cost_repo
        self._project_repo = project_repo
        self._task_repo = task_repo

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
    ) -> CostItem:
        if not self._project_repo.get(project_id):
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        if task_id is not None and not self._task_repo.get(task_id):
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")

        if planned_amount < 0:
            raise ValidationError("Planned amount cannot be negative.")
        
        if committed_amount < 0:
            raise ValidationError("Committed amount cannot be negative.")   
        
        if actual_amount < 0:
            raise ValidationError("Actual amount cannot be negative.")
        
        if incurred_date is not None and not isinstance(incurred_date, date):
            raise ValidationError("Incurred date must be a valid date.")
        

        cost_item = CostItem.create(
            project_id=project_id,
            task_id=task_id,
            description=description.strip(),
            planned_amount=planned_amount,
            committed_amount=committed_amount,
            actual_amount=actual_amount,
            cost_type=cost_type,
            incurred_date=incurred_date,
            currency_code = currency_code
        )

        try:
            self._cost_repo.add(cost_item)
            self._session.commit()
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
        currency_code: str | None = None
    ) -> CostItem:
        item = self._cost_repo.get(cost_id)
        if not item:
            raise NotFoundError("Cost item not found.", code="COST_NOT_FOUND")

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
                raise ValidationError("Actual amount cannot be negative.")
            item.committed_amount = committed_amount
        
        if cost_type is not None:
            item.cost_type = cost_type
        
        if incurred_date is not None:
            item.incurred_date = incurred_date
        
        if currency_code is not None:
            item.currency_code = currency_code.strip() or None    
        

        try:
            self._cost_repo.update(item)
            self._session.commit()
        except Exception as e:
            self._session.rollback()
            raise e
        
        domain_events.costs_changed.emit(item.project_id)
        return item

    def delete_cost_item(self, cost_id: str) -> None:
        item = self._cost_repo.get(cost_id)
        if not item:
            raise NotFoundError("Cost item not found.", code="COST_NOT_FOUND")
        try:
            self._cost_repo.delete(cost_id)
            self._session.commit()
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

        return {
            "project_id": project_id,
            "total_planned": total_planned,
            "total-committed": total_committed,
            "total_actual": total_actual,
            "variance_actual": total_actual - total_planned,
            "variance_committment": total_committed - total_planned,
            "exposure": total_committed + total_actual,
            "items_count": len(items),
        }