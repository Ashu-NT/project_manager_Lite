from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeEventType,
)
from src.core.modules.project_management.application.financials.financial_changes.policy import (
    FinancialChangeAuditPolicy,
    FinancialChangeValidationPolicy,
)
from src.core.modules.project_management.contracts.approval import (
    pm_reviewer_permission,
)
from src.core.modules.project_management.contracts.ports.scheduling.schedule_change import (
    ApprovedScheduleChangePort,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpactType,
    FinancialChangeRequest,
)
from src.core.platform.application.approval.approval_mutation_participant import (
    request_approval_using,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
)
from src.core.platform.contract.repositories.approval.contracts import (
    ApprovalRepository,
)
from src.core.shared.time.clock import CalendarClock


class FinancialChangeSubmissionCommandHandler(
    FinancialChangeValidationPolicy, FinancialChangeAuditPolicy
):
    """Submit governed changes without opening or committing a transaction."""

    def __init__(
        self,
        *,
        session: Session,
        change_repo: FinancialChangeRepository,
        budget_repo: ProjectBudgetRepository,
        forecast_repo: ProjectForecastRepository,
        task_service: ApprovedScheduleChangePort,
        clock: CalendarClock,
        approval_repo: ApprovalRepository | None = None,
        record_event: Callable[[object], None] | None = None,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
    ) -> None:
        self._session = session
        self._change_repo = change_repo
        self._budget_repo = budget_repo
        self._forecast_repo = forecast_repo
        self._task_service = task_service
        self._clock = clock
        self._approval_repo = approval_repo
        self._record_event = record_event
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service

    def submit_change(
        self,
        change_id: str,
        *,
        submitted_by: str,
        expected_version: int,
    ) -> FinancialChangeRequest:

        if self._approval_repo is None or self._record_event is None:
            raise BusinessRuleError(
                "Financial change submission requires the Finance governance command boundary.",
                code="FINANCIAL_CHANGE_COMMAND_BOUNDARY_REQUIRED",
            )
        change = self._require_change(change_id)
        self._require_project_permission(
            change.project_id, "financial_change.manage", "submit financial change"
        )
        change.ensure_draft()
        if change.row_version != expected_version:
            raise ConcurrencyError(
                "Financial change was updated since you opened it.", code="STALE_WRITE"
            )
        require_permission(
            self._user_session,
            "approval.request",
            operation_label="submit financial change for approval",
        )
        require_project_permission(
            self._user_session,
            change.project_id,
            "approval.request",
            operation_label="submit financial change for approval",
        )
        impacts = self._change_repo.list_impacts(change.id)
        if not impacts:
            raise BusinessRuleError(
                "Cannot submit a financial change without impacts.",
                code="FINANCIAL_CHANGE_EMPTY",
            )
        types = {row.impact_type for row in impacts}
        if FinancialChangeImpactType.BUDGET in types:
            current_budget = self._budget_repo.get_approved_for_project(
                change.project_id
            )
            if (
                current_budget is None
                or current_budget.id != change.base_budget_id
                or current_budget.revision != change.base_budget_revision
            ):
                raise ConcurrencyError(
                    "The approved budget changed after this financial change was drafted.",
                    code="FINANCIAL_CHANGE_BUDGET_BASE_STALE",
                )
            if self._budget_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open budget version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_BUDGET_EXISTS",
                )
        if FinancialChangeImpactType.FORECAST in types:
            current_forecast = self._forecast_repo.get_approved_for_project(
                change.project_id
            )
            if (
                current_forecast is None
                or current_forecast.id != change.base_forecast_id
                or current_forecast.revision != change.base_forecast_revision
            ):
                raise ConcurrencyError(
                    "The approved forecast changed after this financial change was drafted.",
                    code="FINANCIAL_CHANGE_FORECAST_BASE_STALE",
                )
            if self._forecast_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open forecast version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_FORECAST_EXISTS",
                )
        self._task_service._validate_approved_schedule_changes(
            self._schedule_commands(change, impacts)
        )
        scope = self._require_context("submit financial change for approval")
        principal = self._user_session.principal if self._user_session else None
        approval = request_approval_using(
            approval_repo=self._approval_repo,
            enterprise_audit_service=self._enterprise_audit_service,
            clock=self._clock,
            record_event=self._record_event,
            request_type="financial_change.apply",
            decision_permission=pm_reviewer_permission("financial_change.apply"),
            entity_type="financial_change_request",
            entity_id=change.id,
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=change.project_id,
            payload={"change_id": change.id},
            requested_by_user_id=principal.user_id if principal else None,
            requested_by_username=principal.username if principal else None,
        )
        change.submit(
            approval_request_id=approval.id,
            submitted_by=submitted_by,
            submitted_at=self._clock.now(),
        )
        self._change_repo.update(change, expected_row_version=expected_version)
        self._audit_change("submit", change)
        self._session.flush()
        self._emit_change_event(change, FinancialChangeEventType.SUBMITTED)
        return change


__all__ = ["FinancialChangeSubmissionCommandHandler"]
