from __future__ import annotations

from collections.abc import Callable
from datetime import date, datetime
from typing import Protocol

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
    FinancialChangeEventType,
)
from src.core.modules.project_management.application.financials.governance.successors.dto.responses.financial_successors import (
    ApprovedFinancialLineAdjustment,
    ApprovedFinancialSuccessorResult,
)
from src.core.modules.project_management.contracts.ports.scheduling.schedule_change import (
    ApprovedScheduleChangePort,
    ApprovedTaskScheduleChange,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.forecasts.forecast import (
    ProjectForecastRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    ProjectBudget,
)
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeImpactType,
    FinancialChangeRequest,
)
from src.core.modules.project_management.domain.financials.forecast import (
    ForecastLine,
    ProjectForecast,
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
    NotFoundError,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry


class ApprovedBudgetChangeAuthority(Protocol):
    """Budget-owner capability joining the approval caller's transaction."""

    def _apply_approved_financial_change(
        self,
        *,
        base_budget_id: str,
        expected_base_revision: int,
        project_id: str,
        name: str,
        reason: str,
        actor_id: str,
        adjustments: tuple[ApprovedFinancialLineAdjustment, ...],
        occurred_at: datetime,
    ) -> ApprovedFinancialSuccessorResult: ...


class ApprovedForecastChangeAuthority(Protocol):
    """Forecast-owner capability joining the approval caller's transaction."""

    def _apply_approved_financial_change(
        self,
        *,
        base_forecast_id: str,
        expected_base_revision: int,
        project_id: str,
        name: str,
        reason: str,
        actor_id: str,
        as_of_date: date,
        adjustments: tuple[ApprovedFinancialLineAdjustment, ...],
        occurred_at: datetime,
    ) -> ApprovedFinancialSuccessorResult: ...


class FinancialChangeAccessPolicy(ProjectManagementModuleGuardMixin):
    """Authorization and scoped repository access for explicitly injected handlers."""

    _change_repo: FinancialChangeRepository
    _tenant_context_service: TenantContextService | None

    def _require_change(self, change_id: str) -> FinancialChangeRequest:
        change = self._change_repo.get(change_id)
        if change is None:
            raise NotFoundError(
                "Financial change not found.", code="FINANCIAL_CHANGE_NOT_FOUND"
            )
        return change

    def _require_project_permission(
        self, project_id: str, permission: str, operation: str
    ) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )

    def _require_context(self, operation: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required for financial change control.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation
        )


class FinancialChangeValidationPolicy(FinancialChangeAccessPolicy):
    """Shared draft and approved-base invariants; never constructs dependencies."""

    _budget_repo: ProjectBudgetRepository
    _forecast_repo: ProjectForecastRepository
    _financial_profile_repo: ProjectFinancialProfileRepository
    _cost_code_repo: ProjectCostCodeRepository
    _task_repo: TaskRepository
    _task_service: ApprovedScheduleChangePort

    @staticmethod
    def _schedule_commands(
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
    ) -> list[ApprovedTaskScheduleChange]:
        return [
            ApprovedTaskScheduleChange(
                reference_id=impact.id,
                project_id=change.project_id,
                task_id=impact.task_id or "",
                expected_version=impact.target_task_version or 0,
                start_date=impact.schedule_start,
                finish_date=impact.schedule_finish,
            )
            for impact in impacts
            if impact.impact_type is FinancialChangeImpactType.SCHEDULE
        ]

    def _validate_target(
        self, change: FinancialChangeRequest, impact: FinancialChangeImpact
    ) -> None:
        if not impact.target_line_id:
            return
        line: BudgetLine | ForecastLine
        if impact.impact_type is FinancialChangeImpactType.BUDGET:
            budget_line = self._budget_repo.get_line(impact.target_line_id)
            if budget_line is None or budget_line.budget_id != change.base_budget_id:
                raise NotFoundError(
                    "Target approved budget line not found.",
                    code="FINANCIAL_CHANGE_BUDGET_TARGET_NOT_FOUND",
                )
            line = budget_line
        elif impact.impact_type is FinancialChangeImpactType.FORECAST:
            forecast_line = self._forecast_repo.get_line(impact.target_line_id)
            if (
                forecast_line is None
                or forecast_line.forecast_id != change.base_forecast_id
            ):
                raise NotFoundError(
                    "Target approved forecast line not found.",
                    code="FINANCIAL_CHANGE_FORECAST_TARGET_NOT_FOUND",
                )
            line = forecast_line
        else:
            raise BusinessRuleError(
                "Only budget and forecast impacts may target canonical financial lines.",
                code="FINANCIAL_CHANGE_TARGET_TYPE_INVALID",
            )
        if line.project_id != change.project_id:
            raise BusinessRuleError(
                "Target line does not belong to the financial change project.",
                code="FINANCIAL_CHANGE_TARGET_PROJECT_MISMATCH",
            )
        if line.cost_code_id != impact.cost_code_id or line.task_id != impact.task_id:
            raise BusinessRuleError(
                "Impact dimensions must match the target canonical line.",
                code="FINANCIAL_CHANGE_TARGET_DIMENSION_MISMATCH",
            )

    def _validate_application_bases(
        self,
        change: FinancialChangeRequest,
        impacts: list[FinancialChangeImpact],
    ) -> None:
        types = {row.impact_type for row in impacts}
        if FinancialChangeImpactType.BUDGET in types:
            self._require_base_budget(change)
            if self._budget_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open budget version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_BUDGET_EXISTS",
                )
        if FinancialChangeImpactType.FORECAST in types:
            self._require_base_forecast(change)
            if self._forecast_repo.has_open_for_project(change.project_id):
                raise BusinessRuleError(
                    "An open forecast version must be resolved before applying a financial change.",
                    code="FINANCIAL_CHANGE_OPEN_FORECAST_EXISTS",
                )
        schedule_commands = self._schedule_commands(change, impacts)
        self._task_service._validate_approved_schedule_changes(schedule_commands)

    def _require_base_budget(self, change: FinancialChangeRequest) -> ProjectBudget:
        current = self._budget_repo.get_approved_for_project(change.project_id)
        if (
            current is None
            or current.id != change.base_budget_id
            or current.revision != change.base_budget_revision
        ):
            raise ConcurrencyError(
                "The approved budget changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_BUDGET_BASE_STALE",
            )
        return current

    def _require_base_forecast(self, change: FinancialChangeRequest) -> ProjectForecast:
        current = self._forecast_repo.get_approved_for_project(change.project_id)
        if (
            current is None
            or current.id != change.base_forecast_id
            or current.revision != change.base_forecast_revision
        ):
            raise ConcurrencyError(
                "The approved forecast changed after this financial change was drafted.",
                code="FINANCIAL_CHANGE_FORECAST_BASE_STALE",
            )
        return current

    def _require_mutable_change(
        self, change_id: str, expected_version: int, operation: str
    ) -> FinancialChangeRequest:
        change = self._require_change(change_id)
        self._require_project_permission(
            change.project_id, "financial_change.manage", operation
        )
        change.ensure_draft()
        if change.row_version != expected_version:
            raise ConcurrencyError(
                "Financial change was updated since you opened it.", code="STALE_WRITE"
            )
        return change

    def _require_impact(self, impact_id: str) -> FinancialChangeImpact:
        impact = self._change_repo.get_impact(impact_id)
        if impact is None:
            raise NotFoundError(
                "Financial change impact not found.",
                code="FINANCIAL_CHANGE_IMPACT_NOT_FOUND",
            )
        return impact

    def _require_cost_code(
        self, project_id: str, cost_code_id: str, effective_date: date
    ) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError("Cost code not found.", code="COST_CODE_NOT_FOUND")
        if not cost_code.is_effective_on(effective_date):
            raise BusinessRuleError(
                "Cost code is not effective on the financial change date.",
                code="FINANCIAL_CHANGE_COST_CODE_INACTIVE",
            )
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile and profile.cost_code_policy is CostCodePolicy.RESTRICTED:
            allowed = {
                row.cost_code_id
                for row in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed:
                raise BusinessRuleError(
                    "Cost code is not permitted for this project.",
                    code="FINANCIAL_CHANGE_COST_CODE_NOT_PERMITTED",
                )

    def _require_task(self, project_id: str, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise BusinessRuleError(
                "Task does not belong to the financial change project.",
                code="FINANCIAL_CHANGE_TASK_PROJECT_MISMATCH",
            )
        return task


class FinancialChangeAuditPolicy:
    """Stage audit, activity and change facts in the caller-owned transaction."""

    _record_event: Callable[[object], None] | None

    def _emit_change_event(
        self,
        change: FinancialChangeRequest,
        change_type: FinancialChangeEventType,
        *,
        impact_id: str | None = None,
    ) -> None:
        if self._record_event is None:
            return
        self._record_event(
            FinancialChangeChanged(
                tenant_id=change.tenant_id,
                organization_id=change.organization_id,
                project_id=change.project_id,
                change_id=change.id,
                change_type=change_type,
                impact_id=impact_id,
                occurred_at=change.updated_at,
            )
        )

    def _audit_change(self, operation: str, change: FinancialChangeRequest) -> None:
        self._audit_change_using(self, operation, change)

    @staticmethod
    def _audit_change_using(
        owner, operation: str, change: FinancialChangeRequest
    ) -> None:
        """Record the change audit through the current transaction-bound owner."""
        full_operation = f"financial_change.{operation}"
        snapshot = {
            "revision": change.revision,
            "status": change.status.value,
            "base_budget_id": change.base_budget_id,
            "base_forecast_id": change.base_forecast_id,
            "applied_budget_id": change.applied_budget_id,
            "applied_forecast_id": change.applied_forecast_id,
            "applied_schedule_count": change.applied_schedule_count,
        }
        record_audit_entry(
            owner,
            operation=full_operation,
            entity_type="financial_change_request",
            entity_id=change.id,
            entity_parent_id=change.project_id,
            module="project_management",
            category="APPROVAL",
            after_data=snapshot,
            workspace_id=change.project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            owner,
            action=full_operation,
            entity_type="financial_change_request",
            entity_id=change.id,
            parent_entity_id=change.project_id,
            module="project_management",
            workspace_id=change.project_id,
            details={"action": operation},
            commit=False,
        )

    def _audit_impact(
        self,
        operation: str,
        change: FinancialChangeRequest,
        impact: FinancialChangeImpact,
    ) -> None:
        full_operation = f"financial_change_impact.{operation}"
        snapshot = {
            "impact_type": impact.impact_type.value,
            "amount": str(impact.amount),
            "currency_code": impact.currency_code,
            "target_line_id": impact.target_line_id,
            "target_task_version": impact.target_task_version,
        }
        record_audit_entry(
            self,
            operation=full_operation,
            entity_type="financial_change_impact",
            entity_id=impact.id,
            entity_parent_id=change.id,
            module="project_management",
            category="FINANCIAL",
            after_data=snapshot,
            workspace_id=change.project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=full_operation,
            entity_type="financial_change_impact",
            entity_id=impact.id,
            parent_entity_id=change.id,
            module="project_management",
            workspace_id=change.project_id,
            details={"action": operation},
            commit=False,
        )

    def _audit_version(
        self,
        entity_type: str,
        entity_id: str,
        change: FinancialChangeRequest,
        occurred_at: datetime,
    ) -> None:
        full_operation = f"{entity_type}.apply_financial_change"
        record_audit_entry(
            self,
            operation=full_operation,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_parent_id=change.project_id,
            module="project_management",
            category="FINANCIAL",
            after_data={
                "financial_change_id": change.id,
                "applied_at": occurred_at.isoformat(),
            },
            workspace_id=change.project_id,
            source="application",
            severity="high",
            metadata={"action": "apply_financial_change"},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=full_operation,
            entity_type=entity_type,
            entity_id=entity_id,
            parent_entity_id=change.project_id,
            module="project_management",
            workspace_id=change.project_id,
            details={"action": "apply_financial_change"},
            commit=False,
        )
