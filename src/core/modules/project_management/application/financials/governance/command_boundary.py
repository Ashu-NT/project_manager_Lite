from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.application.financials.commitments.commitment_service import (
    ProjectCommitmentService,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_service import (
    ProjectCostEntryService,
)
from src.core.modules.project_management.application.financials.configuration_service import (
    FinancialConfigurationService,
)
from src.core.modules.project_management.application.financials.financial_changes.service import (
    FinancialChangeService,
)
from src.core.modules.project_management.application.financials.forecasts.generation_service import (
    ForecastGenerationService,
)
from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.application.financials.invoicing.billing_profile_service import (
    ProjectBillingProfileService,
)
from src.core.modules.project_management.application.financials.invoicing.preparation_service import (
    ProjectBillingPreparationService,
)
from src.core.modules.project_management.application.financials.planned_costs.planned_cost_service import (
    PlannedCostService,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_service import (
    ProjectRateCardService,
)
from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import (
    FinanceGovernanceUnitOfWork,
    FinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext


logger = logging.getLogger(__name__)
T = TypeVar("T")


@dataclass(slots=True)
class FinanceGovernanceOperations:
    """Transaction-neutral services bound to one operation-scoped Finance UoW."""

    budgets: BudgetService
    forecast_versions: ForecastVersionService
    forecast_generation: ForecastGenerationService
    financial_changes: FinancialChangeService
    financial_setup: FinancialConfigurationService
    rate_cards: ProjectRateCardService
    planned_costs: PlannedCostService
    commitments: ProjectCommitmentService
    cost_entries: ProjectCostEntryService
    billing_profiles: ProjectBillingProfileService
    billing_preparations: ProjectBillingPreparationService
    post_commit_actions: list[Callable[[], None]] = field(default_factory=list)


class FinanceGovernanceCommandBoundary:
    """The sole outward transaction owner for R6C Finance governance commands."""

    def __init__(
        self,
        *,
        uow_factory: FinanceGovernanceUnitOfWorkFactory,
        operations_factory: Callable[
            [FinanceGovernanceUnitOfWork], FinanceGovernanceOperations
        ],
        prepare_command: Callable[[], None] | None = None,
    ) -> None:
        self._uow_factory = uow_factory
        self._operations_factory = operations_factory
        self._prepare_command = prepare_command

    def budget(
        self,
        command: Callable[[BudgetService], T],
    ) -> T:
        return self._execute(lambda operations: command(operations.budgets))

    def forecast_version(
        self,
        command: Callable[[ForecastVersionService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.forecast_versions),
        )

    def forecast_generation(
        self,
        command: Callable[[ForecastGenerationService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.forecast_generation),
        )

    def financial_change(
        self,
        command: Callable[[FinancialChangeService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.financial_changes),
        )

    def planned_cost(
        self,
        command: Callable[[PlannedCostService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.planned_costs),
        )

    def commitment(
        self,
        command: Callable[[ProjectCommitmentService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.commitments),
        )

    def cost_entry(
        self,
        command: Callable[[ProjectCostEntryService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.cost_entries),
        )

    def financial_setup(
        self,
        command: Callable[[FinancialConfigurationService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.financial_setup),
        )

    def rate_card(
        self,
        command: Callable[[ProjectRateCardService], T],
    ) -> T:
        return self._execute(
            lambda operations: command(operations.rate_cards),
        )

    def billing_profile(
        self,
        command: Callable[[ProjectBillingProfileService], T],
    ) -> T:
        return self._execute(lambda operations: command(operations.billing_profiles))

    def billing_preparation(
        self,
        command: Callable[[ProjectBillingPreparationService], T],
    ) -> T:
        return self._execute(lambda operations: command(operations.billing_preparations))

    def _execute(self, command: Callable[[FinanceGovernanceOperations], T]) -> T:
        if self._prepare_command is not None:
            self._prepare_command()
        context = DomainEventContext(correlation_id=generate_id())
        post_commit_actions: tuple[Callable[[], None], ...]
        with self._uow_factory.create(context=context) as uow:
            operations = self._operations_factory(uow)
            result = command(operations)
            post_commit_actions = tuple(operations.post_commit_actions)
            uow.commit()

        for action in post_commit_actions:
            self._run_post_commit(action)
        return result

    @classmethod
    def _run_post_commit(cls, callback: Callable[..., None], *args: Any) -> None:
        try:
            callback(*args)
        except Exception:
            logger.exception("Finance governance post-commit reaction failed")


class FinanceGovernedServicePort:
    """Read delegation plus canonical command routing for one Finance service family.

    Command services resolve and authorize their own scoped aggregates inside the fresh
    operation UoW. The port deliberately performs no pre-read identity resolution.
    """

    def __init__(
        self,
        *,
        read_service: object,
        boundary: FinanceGovernanceCommandBoundary,
        family: str,
        mutations: frozenset[str],
    ) -> None:
        self._read_service = read_service
        self._boundary = boundary
        self._family = family
        self._mutations = mutations

    def __getattr__(self, name: str):
        attribute = getattr(self._read_service, name)
        if name not in self._mutations or not callable(attribute):
            return attribute

        def governed(*args, **kwargs):
            executor = getattr(self._boundary, self._family)
            return executor(lambda service: getattr(service, name)(*args, **kwargs))

        return governed


__all__ = [
    "FinanceGovernanceCommandBoundary",
    "FinanceGovernanceOperations",
    "FinanceGovernedServicePort",
]
