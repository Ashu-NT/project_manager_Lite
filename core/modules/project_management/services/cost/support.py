from __future__ import annotations

from datetime import date

from core.platform.common.exceptions import NotFoundError, ValidationError
from core.modules.project_management.domain.enums import CostType
from core.platform.approval.policy import is_governance_required
from core.platform.access.authorization import require_project_permission
from core.platform.auth.authorization import is_admin_session, require_permission

DEFAULT_CURRENCY_CODE = "EUR"


class CostSupportMixin:
    def _is_governed(self, *, operation_code: str, bypass_approval: bool) -> bool:
        return (
            not bypass_approval
            and self._approval_service is not None
            and is_governance_required(operation_code)
            and not is_admin_session(self._user_session)
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
    def _validate_non_negative(value: float, label: str) -> float:
        amount = float(value)
        if amount < 0:
            raise ValidationError(f"{label} cannot be negative.")
        return amount

    @staticmethod
    def _validate_incurred_date(incurred_date: date | None) -> date | None:
        if incurred_date is not None and not isinstance(incurred_date, date):
            raise ValidationError("Incurred date must be a valid date.")
        return incurred_date

    @staticmethod
    def _normalize_cost_type(cost_type: CostType | str) -> CostType:
        if isinstance(cost_type, CostType):
            return cost_type
        return CostType(str(cost_type))

    @staticmethod
    def _normalize_currency(currency_code: str | None) -> str:
        return (currency_code or "").strip().upper() or DEFAULT_CURRENCY_CODE
