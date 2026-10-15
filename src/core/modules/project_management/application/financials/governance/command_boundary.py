from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

from src.core.modules.project_management.application.financials.accounting.commands.request import (
    AccountingHandoffRequestCommandHandler,
)
from src.core.modules.project_management.application.financials.budgets.commands import (
    BudgetApprovalCommands,
    BudgetLifecycleCommands,
    BudgetLineCommands,
)
from src.core.modules.project_management.application.financials.configuration.commands import (
    CostCodeCommandHandler,
    FinancialProfileCommandHandler,
)
from src.core.modules.project_management.application.financials.cost.entries.commands import (
    ProjectCostEntryLifecycleCommandHandler,
    ProjectCostEntryPostingCommandHandler,
    ProjectCostEntryReviewCommandHandler,
)
from src.core.modules.project_management.application.financials.financial_changes.commands import (
    FinancialChangeDraftCommandHandler,
    FinancialChangeSubmissionCommandHandler,
)
from src.core.modules.project_management.application.financials.forecasts.commands import (
    ForecastApprovalCommands,
    ForecastGenerationCommands,
    ForecastLifecycleCommands,
    ForecastLineCommands,
)
from src.core.modules.project_management.application.financials.invoicing.commands import (
    BillingPreparationSourceCommandHandler,
    BillingPreparationSubmissionCommandHandler,
    PreparationLifecycleCommandHandler,
    ProjectBillingProfileCommandHandler,
    ProjectBillingScheduleCommandHandler,
)
from src.core.modules.project_management.application.financials.planned_costs.commands import (
    PlannedCostCommandHandler,
)
from src.core.modules.project_management.application.financials.rate_cards.commands import (
    ProjectRateCardCommandHandler,
    RateCardLineCommandHandler,
)
from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import (
    FinanceGovernanceUnitOfWork,
    FinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext

T = TypeVar("T")


@dataclass(slots=True)
class FinanceGovernanceOperations:
    """Explicit command capabilities bound to one operation-scoped Finance UoW."""

    budget_lifecycle: BudgetLifecycleCommands
    budget_lines: BudgetLineCommands
    budget_approvals: BudgetApprovalCommands
    forecast_lifecycle: ForecastLifecycleCommands
    forecast_lines: ForecastLineCommands
    forecast_approvals: ForecastApprovalCommands
    forecast_generation: ForecastGenerationCommands
    financial_changes: FinancialChangeDraftCommandHandler
    financial_change_submissions: FinancialChangeSubmissionCommandHandler
    financial_profiles: FinancialProfileCommandHandler
    cost_codes: CostCodeCommandHandler
    rate_cards: ProjectRateCardCommandHandler
    rate_lines: RateCardLineCommandHandler
    planned_costs: PlannedCostCommandHandler
    cost_entries: ProjectCostEntryLifecycleCommandHandler
    cost_reviews: ProjectCostEntryReviewCommandHandler
    cost_postings: ProjectCostEntryPostingCommandHandler
    billing_profiles: ProjectBillingProfileCommandHandler
    billing_preparations: PreparationLifecycleCommandHandler
    billing_sources: BillingPreparationSourceCommandHandler
    billing_submissions: BillingPreparationSubmissionCommandHandler
    billing_schedules: ProjectBillingScheduleCommandHandler
    accounting_handoffs: AccountingHandoffRequestCommandHandler


class FinanceGovernanceCommandBoundary:
    """Own the fresh transaction; handlers own their feature business operations."""

    def __init__(
        self, *, uow_factory: FinanceGovernanceUnitOfWorkFactory,
        operations_factory: Callable[[FinanceGovernanceUnitOfWork], FinanceGovernanceOperations],
        prepare_command: Callable[[], None] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._operations_factory = operations_factory
        self._prepare_command = prepare_command

    def budget_lifecycle(self, command: Callable[[BudgetLifecycleCommands], T]) -> T:
        return self._execute(lambda operations: command(operations.budget_lifecycle))

    def budget_lines(self, command: Callable[[BudgetLineCommands], T]) -> T:
        return self._execute(lambda operations: command(operations.budget_lines))

    def budget_approval(self, command: Callable[[BudgetApprovalCommands], T]) -> T:
        return self._execute(lambda operations: command(operations.budget_approvals))

    def forecast_lifecycle(self, command: Callable[[ForecastLifecycleCommands], T]) -> T:
        return self._execute(lambda operations: command(operations.forecast_lifecycle))

    def forecast_lines(self, command: Callable[[ForecastLineCommands], T]) -> T:
        return self._execute(lambda operations: command(operations.forecast_lines))

    def forecast_approval(self, command: Callable[[ForecastApprovalCommands], T]) -> T:
        return self._execute(lambda operations: command(operations.forecast_approvals))

    def forecast_generation(self, command: Callable[[ForecastGenerationCommands], T]) -> T:
        return self._execute(lambda operations: command(operations.forecast_generation))

    def financial_change(self, command: Callable[[FinancialChangeDraftCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.financial_changes))

    def financial_change_submission(self, command: Callable[[FinancialChangeSubmissionCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.financial_change_submissions))

    def financial_profile(self, command: Callable[[FinancialProfileCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.financial_profiles))

    def cost_code(self, command: Callable[[CostCodeCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.cost_codes))

    def rate_card(self, command: Callable[[ProjectRateCardCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.rate_cards))

    def rate_line(self, command: Callable[[RateCardLineCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.rate_lines))

    def planned_cost(self, command: Callable[[PlannedCostCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.planned_costs))

    def cost_entry(self, command: Callable[[ProjectCostEntryLifecycleCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.cost_entries))

    def cost_entry_review(self, command: Callable[[ProjectCostEntryReviewCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.cost_reviews))

    def cost_entry_posting(self, command: Callable[[ProjectCostEntryPostingCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.cost_postings))

    def billing_profile(self, command: Callable[[ProjectBillingProfileCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.billing_profiles))

    def billing_preparation(self, command: Callable[[PreparationLifecycleCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.billing_preparations))

    def billing_source(self, command: Callable[[BillingPreparationSourceCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.billing_sources))

    def billing_submission(self, command: Callable[[BillingPreparationSubmissionCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.billing_submissions))

    def billing_schedule(self, command: Callable[[ProjectBillingScheduleCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.billing_schedules))

    def accounting_handoff(self, command: Callable[[AccountingHandoffRequestCommandHandler], T]) -> T:
        return self._execute(lambda operations: command(operations.accounting_handoffs))

    def _execute(self, command: Callable[[FinanceGovernanceOperations], T]) -> T:
        if self._prepare_command is not None:
            self._prepare_command()
        context = DomainEventContext(correlation_id=generate_id())
        with self._uow_factory.create(context=context) as uow:
            operations = self._operations_factory(uow)
            result = command(operations)
            uow.commit()
        return result


__all__ = ["FinanceGovernanceCommandBoundary", "FinanceGovernanceOperations"]
