from __future__ import annotations

from datetime import date

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, ValidationError
from core.platform.common.models import CostItem, CostType
from core.platform.audit.helpers import record_audit


class CostLifecycleMixin:
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
        governed = self._is_governed(operation_code="cost.add", bypass_approval=bypass_approval)
        self._require_operation_permission(
            project_id=project_id,
            governed=governed,
            manage_permission="cost.manage",
            manage_label="add cost item",
            request_label="request cost item creation",
        )
        project = self._require_project(project_id)
        task = self._resolve_task_for_project(project_id=project_id, task_id=task_id)
        normalized_cost_type = self._normalize_cost_type(cost_type)
        planned_amount = self._validate_non_negative(planned_amount, "Planned amount")
        committed_amount = self._validate_non_negative(committed_amount, "Committed amount")
        actual_amount = self._validate_non_negative(actual_amount, "Actual amount")
        incurred_date = self._validate_incurred_date(incurred_date)
        resolved_currency = self._normalize_currency(currency_code)

        if governed:
            req = self._approval_service.request_change(
                request_type="cost.add",
                entity_type="cost_item",
                entity_id=task_id or project_id,
                project_id=project_id,
                payload={
                    "project_id": project_id,
                    "task_id": task_id,
                    "task_name": task.name if task is not None else None,
                    "project_name": project.name,
                    "description": description,
                    "planned_amount": planned_amount,
                    "committed_amount": committed_amount,
                    "actual_amount": actual_amount,
                    "cost_type": normalized_cost_type.value,
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
            cost_type=normalized_cost_type,
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
        except Exception:
            self._session.rollback()
            raise

        domain_events.costs_changed.emit(project_id)
        return cost_item

    def update_cost_item(
        self,
        cost_id: str,
        description: str | None = None,
        planned_amount: float | None = None,
        committed_amount: float | None = None,
        actual_amount: float | None = None,
        cost_type: CostType | None = None,
        incurred_date: date | None = None,
        currency_code: str | None = None,
        expected_version: int | None = None,
        bypass_approval: bool = False,
    ) -> CostItem:
        governed = self._is_governed(operation_code="cost.update", bypass_approval=bypass_approval)
        item = self._require_cost_item(cost_id)
        self._require_operation_permission(
            project_id=item.project_id,
            governed=governed,
            manage_permission="cost.manage",
            manage_label="update cost item",
            request_label="request cost item update",
        )
        if expected_version is not None and item.version != expected_version:
            raise ConcurrencyError(
                "Cost item changed since you opened it. Refresh and try again.",
                code="STALE_WRITE",
            )
        item_task = self._task_repo.get(item.task_id) if item.task_id else None
        if governed:
            req = self._approval_service.request_change(
                request_type="cost.update",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                payload={
                    "cost_id": cost_id,
                    "description": description,
                    "task_name": item_task.name if item_task is not None else None,
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
            item.planned_amount = self._validate_non_negative(planned_amount, "Planned amount")
        if actual_amount is not None:
            item.actual_amount = self._validate_non_negative(actual_amount, "Actual amount")
        if committed_amount is not None:
            item.committed_amount = self._validate_non_negative(committed_amount, "Committed amount")
        if cost_type is not None:
            item.cost_type = self._normalize_cost_type(cost_type)
        if incurred_date is not None:
            item.incurred_date = self._validate_incurred_date(incurred_date)
        if currency_code is not None:
            item.currency_code = self._normalize_currency(currency_code)

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
        except Exception:
            self._session.rollback()
            raise

        domain_events.costs_changed.emit(item.project_id)
        return item

    def delete_cost_item(self, cost_id: str, bypass_approval: bool = False) -> None:
        governed = self._is_governed(operation_code="cost.delete", bypass_approval=bypass_approval)
        item = self._require_cost_item(cost_id)
        self._require_operation_permission(
            project_id=item.project_id,
            governed=governed,
            manage_permission="cost.manage",
            manage_label="delete cost item",
            request_label="request cost item deletion",
        )
        item_task = self._task_repo.get(item.task_id) if item.task_id else None
        if governed:
            req = self._approval_service.request_change(
                request_type="cost.delete",
                entity_type="cost_item",
                entity_id=item.id,
                project_id=item.project_id,
                payload={
                    "cost_id": cost_id,
                    "description": item.description,
                    "task_name": item_task.name if item_task is not None else None,
                },
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
        except Exception:
            self._session.rollback()
            raise

        domain_events.costs_changed.emit(item.project_id)
