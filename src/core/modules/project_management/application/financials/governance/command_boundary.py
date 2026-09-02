from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
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
from src.core.modules.project_management.application.financials.rate_cards.rate_card_service import (
    ProjectRateCardService,
)
from src.core.modules.project_management.application.financials.invalidation import (
    invalidation_scope,
)
from src.core.modules.project_management.contracts.uow.finance.finance_governance_unit_of_work import (
    FinanceGovernanceUnitOfWork,
    FinanceGovernanceUnitOfWorkFactory,
)
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events


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
        *,
        project_id: str | None = None,
    ) -> T:
        return self._execute(
            lambda operations: command(operations.budgets),
            invalidation=lambda result: self._emit_budget(result, project_id),
        )

    def forecast_version(
        self,
        command: Callable[[ForecastVersionService], T],
        *,
        project_id: str | None = None,
    ) -> T:
        return self._execute(
            lambda operations: command(operations.forecast_versions),
            invalidation=None,
        )

    def forecast_generation(
        self,
        command: Callable[[ForecastGenerationService], T],
        *,
        project_id: str,
    ) -> T:
        # P19: see `forecast_version` above -- `ForecastGenerationService` records a typed
        # `ForecastDraftGenerated` DomainEvent directly on the transaction's own UoW.
        return self._execute(
            lambda operations: command(operations.forecast_generation),
            invalidation=None,
        )

    def financial_change(
        self,
        command: Callable[[FinancialChangeService], T],
        *,
        project_id: str | None = None,
    ) -> T:
        return self._execute(
            lambda operations: command(operations.financial_changes),
            invalidation=None,
        )

    def financial_setup(
        self,
        command: Callable[[FinancialConfigurationService], T],
        *,
        project_id: str | None = None,
    ) -> T:
        return self._execute(
            lambda operations: command(operations.financial_setup),
            invalidation=None,
        )

    def rate_card(
        self,
        command: Callable[[ProjectRateCardService], T],
        *,
        project_id: str | None = None,
    ) -> T:
        # P22: Rate Card invalidation is driven canonically -- `ProjectRateCardService` records
        # typed DomainEvents (`RateCardCreated`/`RateCardDeactivated`/`RateCardLineAdded`/
        # `RateCardLineUpdated`/`RateCardLineDeactivated`) directly on the transaction's own UoW,
        # dispatched through the shared transactional/post-commit pipeline to the registered
        # ViewInvalidation handler. No legacy signal, no bridge.
        return self._execute(
            lambda operations: command(operations.rate_cards),
            invalidation=None,
        )

    def _execute(
        self,
        command: Callable[[FinanceGovernanceOperations], T],
        *,
        invalidation: Callable[[T], None] | None,
    ) -> T:
        if self._prepare_command is not None:
            self._prepare_command()
        context = DomainEventContext(correlation_id=generate_id())
        post_commit_actions: tuple[Callable[[], None], ...]
        with self._uow_factory.create(context=context) as uow:
            operations = self._operations_factory(uow)
            result = command(operations)
            post_commit_actions = tuple(operations.post_commit_actions)
            uow.commit()

        if invalidation is not None:
            self._run_post_commit(invalidation, result)
        for action in post_commit_actions:
            self._run_post_commit(action)
        return result

    @classmethod
    def _run_post_commit(cls, callback: Callable[..., None], *args: Any) -> None:
        try:
            callback(*args)
        except Exception:
            logger.exception("Finance governance post-commit reaction failed")

    @staticmethod
    def _emit_budget(result: object, fallback_project_id: str | None) -> None:
        project_id = getattr(result, "project_id", None) or fallback_project_id
        if project_id:
            domain_events.budgets_changed.emit(str(project_id))

    @staticmethod
    def _emit_scoped(
        signal_name: str,
        result: object,
        fallback_project_id: str | None,
    ) -> None:
        entity = getattr(result, "forecast", result)
        if not getattr(entity, "tenant_id", None) or not getattr(
            entity, "organization_id", None
        ):
            logger.warning(
                "Finance governance invalidation skipped: result has no tenant scope "
                "signal=%s result_type=%s",
                signal_name,
                type(result).__name__,
            )
            return
        signal = getattr(domain_events, signal_name)
        signal.emit(invalidation_scope(entity, project_id=fallback_project_id))


class FinanceGovernedServicePort:
    """Read delegation plus canonical command routing for one Finance service family."""

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
            project_id = self._project_id(name, args, kwargs)
            executor = getattr(self._boundary, self._family)
            command = lambda service: getattr(service, name)(*args, **kwargs)
            if self._family == "forecast_generation":
                return executor(command, project_id=project_id)
            return executor(command, project_id=project_id or None)

        return governed

    def _project_id(self, name: str, args: tuple, kwargs: dict) -> str:
        explicit = kwargs.get("project_id") or kwargs.get("available_to_project_id")
        if explicit:
            return str(explicit)
        if name in {"create_budget", "create_forecast", "generate_draft", "create_change"}:
            return str(args[0]) if args else ""
        try:
            if self._family == "budget":
                if name in {"add_line"}:
                    return str(self._read_service.get_budget(args[0]).project_id)
                if name in {"update_line", "delete_line"}:
                    line = self._read_service._require_line(args[0])
                    return str(self._read_service.get_budget(line.budget_id).project_id)
                return str(self._read_service.get_budget(args[0]).project_id)
            if self._family == "forecast_version":
                if name == "add_line":
                    return str(self._read_service.get_forecast(args[0]).project_id)
                if name in {"update_line", "delete_line"}:
                    line = self._read_service._require_line(args[0])
                    return str(self._read_service.get_forecast(line.forecast_id).project_id)
                return str(self._read_service.get_forecast(args[0]).project_id)
            if self._family == "financial_change":
                return str(self._read_service.get_change(args[0]).project_id)
        except (AttributeError, IndexError, TypeError):
            return ""
        return ""


__all__ = [
    "FinanceGovernanceCommandBoundary",
    "FinanceGovernanceOperations",
    "FinanceGovernedServicePort",
]
