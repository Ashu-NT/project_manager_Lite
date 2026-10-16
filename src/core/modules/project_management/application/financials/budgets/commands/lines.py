from __future__ import annotations

from collections.abc import Callable
from enum import Enum
from typing import Any, Final

from sqlalchemy.orm import Session

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.budgets._command_values import (
    command_amount as _command_amount,
)
from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetLineChanged,
    BudgetLineChangeType,
)
from src.core.modules.project_management.application.financials.budgets.dto.commands.budget_lines import (
    FinancialAddBudgetLineCommand,
    FinancialDeleteBudgetLineCommand,
    FinancialUpdateBudgetLineCommand,
)
from src.core.modules.project_management.application.financials.budgets.dto.responses.mutations import (
    FinancialBudgetLineMutationDto,
)
from src.core.modules.project_management.application.financials.budgets.mappers.responses import (
    map_budget_line,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
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
from src.core.shared.time.clock import CalendarClock


class _Unset(Enum):
    """Typed sentinel distinguishing "argument omitted" from an explicit None."""

    TOKEN = 0


_UNSET: Final = _Unset.TOKEN

_OPEN_VERSION_CONSTRAINT = "uq_pf_budgets_one_open_per_project"
_APPROVED_CONSTRAINT = "uq_pf_budgets_one_approved_per_project"
_REVISION_CONSTRAINT = "uq_pf_budget_project_revision"


class BudgetLineCommands(ProjectManagementModuleGuardMixin):
    """Mutable financial line commands."""

    def __init__(
        self,
        *,
        session: Session,
        budget_repo: ProjectBudgetRepository,
        financial_profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        task_repo: TaskRepository,
        clock: CalendarClock,
        user_session=None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None = None,
        record_event: Callable[[object], None] | None = None,
    ) -> None:
        self._session = session
        self._budget_repo = budget_repo
        self._financial_profile_repo = financial_profile_repo
        self._cost_code_repo = cost_code_repo
        self._task_repo = task_repo
        self._clock = clock
        self._user_session = user_session
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._record_event = record_event


    def add_line(self, command: FinancialAddBudgetLineCommand) -> FinancialBudgetLineMutationDto:
        amount = _command_amount(command.amount)
        require_permission(self._user_session, "budget.manage", operation_label="add project budget line")
        budget = self._require_budget(command.budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.manage",
            operation_label="add project budget line",
        )
        budget.ensure_mutable()
        if budget.row_version != command.expected_parent_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        resolved_currency = command.currency_code or budget.currency_code
        if resolved_currency != budget.currency_code:
            raise BusinessRuleError(
                "Budget line currency must match the budget's currency.",
                code="PROJECT_BUDGET_LINE_CURRENCY_MISMATCH",
            )
        self._require_eligible_cost_code(budget.project_id, command.cost_code_id)
        if command.task_id is not None:
            self._require_task_in_project(command.task_id, budget.project_id)
        now = self._clock.now()
        line = BudgetLine.create(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            budget_id=budget.id,
            project_id=budget.project_id,
            cost_code_id=command.cost_code_id,
            task_id=command.task_id,
            description=command.description,
            amount=amount,
            currency_code=resolved_currency,
            created_at=now,
        )
        self._budget_repo.add_line(line)
        budget.touch(updated_at=now)
        self._budget_repo.update(budget, expected_row_version=command.expected_parent_version)
        self._record_line_audit(operation="add_line", line=line, budget=budget)
        event = BudgetLineChanged(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            budget_line_id=line.id,
            change_type=BudgetLineChangeType.ADDED,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return map_budget_line(line)


    def update_line(self, command: FinancialUpdateBudgetLineCommand) -> FinancialBudgetLineMutationDto:
        amount = _command_amount(command.amount)
        require_permission(
            self._user_session, "budget.manage", operation_label="update project budget line"
        )
        line = self._require_line(command.budget_line_id)
        budget = self._require_budget(line.budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.manage",
            operation_label="update project budget line",
        )
        budget.ensure_mutable()
        if budget.row_version != command.expected_parent_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        if line.row_version != command.expected_version:
            raise ConcurrencyError("Budget line changed since you opened it.", code="STALE_WRITE")

        resolved_cost_code_id = line.cost_code_id if command.cost_code_id is None else command.cost_code_id
        resolved_task_id = line.task_id if command.task_id is _UNSET else command.task_id
        resolved_currency = line.currency_code if command.currency_code is None else command.currency_code

        if resolved_currency != budget.currency_code:
            raise BusinessRuleError(
                "Budget line currency must match the budget's currency.",
                code="PROJECT_BUDGET_LINE_CURRENCY_MISMATCH",
            )
        if resolved_cost_code_id != line.cost_code_id:
            self._require_eligible_cost_code(budget.project_id, resolved_cost_code_id)
        if resolved_task_id is not None and resolved_task_id != line.task_id:
            self._require_task_in_project(resolved_task_id, budget.project_id)

        now = self._clock.now()
        line.cost_code_id = resolved_cost_code_id
        line.task_id = resolved_task_id
        if command.description is not None:
            line.description = command.description
        if amount is not None:
            line.amount = amount
        line.currency_code = resolved_currency
        line.updated_at = now

        self._budget_repo.update_line(line, expected_row_version=command.expected_version)
        budget.touch(updated_at=now)
        self._budget_repo.update(budget, expected_row_version=command.expected_parent_version)
        self._record_line_audit(operation="update_line", line=line, budget=budget)
        event = BudgetLineChanged(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            budget_line_id=line.id,
            change_type=BudgetLineChangeType.UPDATED,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return map_budget_line(line)


    def delete_line(self, command: FinancialDeleteBudgetLineCommand) -> ProjectBudget:
        require_permission(
            self._user_session, "budget.manage", operation_label="delete project budget line"
        )
        line = self._require_line(command.budget_line_id)
        budget = self._require_budget(line.budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "budget.manage",
            operation_label="delete project budget line",
        )
        budget.ensure_mutable()
        if budget.row_version != command.expected_parent_version:
            raise ConcurrencyError("Budget changed since you opened it.", code="STALE_WRITE")
        # Atomic delete-if-version-matches â€” see delete_budget's note.
        self._budget_repo.delete_line(command.budget_line_id, expected_row_version=command.expected_version)
        now = self._clock.now()
        budget.touch(updated_at=now)
        self._budget_repo.update(budget, expected_row_version=command.expected_parent_version)
        self._record_line_audit(operation="delete_line", line=line, budget=budget)
        event = BudgetLineChanged(
            tenant_id=budget.tenant_id,
            organization_id=budget.organization_id,
            project_id=budget.project_id,
            budget_id=budget.id,
            budget_line_id=line.id,
            change_type=BudgetLineChangeType.REMOVED,
            occurred_at=now,
        )
        if self._record_event is not None:
            self._record_event(event)
        self._session.flush()
        return budget


    def _require_budget(self, budget_id: str) -> ProjectBudget:
        budget = self._budget_repo.get(budget_id)
        if budget is None:
            raise NotFoundError("Project budget not found.", code="PROJECT_BUDGET_NOT_FOUND")
        return budget


    def _require_line(self, line_id: str) -> BudgetLine:
        line = self._budget_repo.get_line(line_id)
        if line is None:
            raise NotFoundError("Project budget line not found.", code="PROJECT_BUDGET_LINE_NOT_FOUND")
        return line


    def _require_eligible_cost_code(self, project_id: str, cost_code_id: str) -> None:
        cost_code = self._cost_code_repo.get(cost_code_id)
        if cost_code is None:
            raise NotFoundError(
                "Cost code not found.", code="PROJECT_BUDGET_LINE_COST_CODE_NOT_FOUND"
            )
        if not cost_code.is_effective_on(self._clock.today()):
            raise BusinessRuleError(
                "Cost code is not active or effective for this date.",
                code="PROJECT_BUDGET_LINE_COST_CODE_INACTIVE",
            )
        profile = self._financial_profile_repo.get_by_project(project_id)
        if profile is not None and profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed_ids = {
                restriction.cost_code_id
                for restriction in self._cost_code_repo.list_restrictions(project_id)
            }
            if cost_code_id not in allowed_ids:
                raise BusinessRuleError(
                    "This cost code is not permitted for this project.",
                    code="PROJECT_BUDGET_LINE_COST_CODE_NOT_PERMITTED",
                )


    def _require_task_in_project(self, task_id: str, project_id: str) -> None:
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        if task.project_id != project_id:
            raise BusinessRuleError(
                "Task does not belong to this project.",
                code="PROJECT_BUDGET_LINE_TASK_PROJECT_MISMATCH",
            )


    def _record_line_audit(self, *, operation: str, line: BudgetLine, budget: ProjectBudget) -> None:
        full_operation = f"project_budget_line.{operation}"
        record_audit_entry(
            self,
            operation=full_operation,
            entity_type="project_budget_line",
            entity_id=line.id,
            entity_parent_id=budget.id,
            module="project_management",
            category="FINANCIAL",
            after_data=self._line_audit_value(line),
            workspace_id=budget.project_id,
            source="application",
            severity="high",
            metadata={"action": operation},
            commit=False,
            fail_closed=True,
        )
        record_activity(
            self,
            action=full_operation,
            entity_type="project_budget_line",
            entity_id=line.id,
            parent_entity_id=budget.id,
            module="project_management",
            workspace_id=budget.project_id,
            details={"action": operation},
            commit=False,
        )


    @staticmethod
    def _line_audit_value(line: BudgetLine) -> dict[str, Any]:
        return {
            "cost_code_id": line.cost_code_id,
            "task_id": line.task_id,
            "amount": str(line.amount),
            "currency_code": line.currency_code,
            "row_version": line.row_version,
        }



__all__ = ["BudgetLineCommands"]
