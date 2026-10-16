from __future__ import annotations

from src.core.modules.project_management.application.financials.budgets.dto.responses.budget_approval import (
    BudgetApprovalResult,
)
from src.core.modules.project_management.application.financials.budgets.dto.responses.mutations import (
    FinancialBudgetLineMutationDto,
    FinancialBudgetMutationDto,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    ProjectBudget,
)


def map_budget(budget: ProjectBudget) -> FinancialBudgetMutationDto:
    return FinancialBudgetMutationDto(
        budget_id=budget.id, project_id=budget.project_id,
        status=budget.status.value, row_version=budget.row_version,
    )


def map_budget_line(line: BudgetLine) -> FinancialBudgetLineMutationDto:
    return FinancialBudgetLineMutationDto(
        budget_line_id=line.id, budget_id=line.budget_id, row_version=line.row_version,
    )


def map_budget_approval(result: BudgetApprovalResult) -> FinancialBudgetMutationDto:
    return FinancialBudgetMutationDto(
        budget_id=result.budget_id, project_id=result.project_id,
        status=result.budget_status.value, row_version=result.row_version,
        approval_request_id=result.approval_request_id or "",
    )
