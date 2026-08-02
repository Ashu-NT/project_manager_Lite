from __future__ import annotations

import json

from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.approval.policy import is_governance_required
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from src.core.shared.audit import record_audit_entry

DEFAULT_CURRENCY_CODE = "EUR"


class CostSupportMixin:
    def _is_governed(self, *, operation_code: str, bypass_approval: bool) -> bool:
        return (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required(operation_code)
        )

    def _require_operation_permission(
        self,
        *,
        project_id: str,
        governed: bool,
        manage_permission: str,
        manage_label: str,
        request_label: str,
    ) -> None:
        if governed:
            require_permission(
                self._user_session,
                "approval.request",
                operation_label=request_label,
            )
            require_project_permission(
                self._user_session,
                project_id,
                "approval.request",
                operation_label=request_label,
            )
            return
        require_permission(self._user_session, manage_permission, operation_label=manage_label)
        require_project_permission(
            self._user_session,
            project_id,
            manage_permission,
            operation_label=manage_label,
        )

    def _require_project(self, project_id: str):
        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return project

    def _require_cost_item(self, cost_id: str):
        item = self._cost_repo.get(cost_id)
        if not item:
            raise NotFoundError("Cost item not found.", code="COST_NOT_FOUND")
        return item

    def _resolve_task_for_project(self, *, project_id: str, task_id: str | None):
        if task_id is None:
            return None
        task = self._task_repo.get(task_id)
        if not task:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise ValidationError(
                "Task must belong to the selected project.",
                code="TASK_PROJECT_MISMATCH",
            )
        return task

    @staticmethod
    def _normalize_currency(currency_code: str | None) -> str:
        return (currency_code or "").strip().upper() or DEFAULT_CURRENCY_CODE

    @staticmethod
    def _cost_audit_value(item) -> str:
        return json.dumps(
            {
                "id": item.id,
                "project_id": item.project_id,
                "task_id": item.task_id,
                "code": item.code,
                "description": item.description,
                "cost_type": (
                    item.cost_type.value
                    if hasattr(item.cost_type, "value")
                    else str(item.cost_type)
                ),
                "planned_amount": item.planned_amount,
                "committed_amount": item.committed_amount,
                "actual_amount": item.actual_amount,
                "forecast_amount": item.forecast_amount,
                "commitment_status": (
                    item.commitment_status.value
                    if hasattr(item.commitment_status, "value")
                    else str(item.commitment_status)
                ),
                "vendor_reference": item.vendor_reference,
                "incurred_date": (
                    item.incurred_date.isoformat() if item.incurred_date else None
                ),
                "currency_code": item.currency_code,
                "version": item.version,
            },
            sort_keys=True,
        )

    def _record_cost_audit(
        self,
        *,
        operation: str,
        item,
        old_item=None,
        approval_request_id: str | None = None,
    ) -> None:
        record_audit_entry(
            self,
            operation=operation,
            entity_type="cost_item",
            entity_id=item.id,
            entity_parent_id=item.project_id,
            module="project_management",
            old_value=(None if old_item is None else self._cost_audit_value(old_item)),
            new_value=(None if operation == "delete" else self._cost_audit_value(item)),
            workspace_id=item.project_id,
            request_id=approval_request_id,
            source="approval" if approval_request_id else "application",
            severity="high",
            compliance_tag="financial",
            metadata={"action": f"cost.{operation}"},
            commit=False,
            fail_closed=True,
        )
