from __future__ import annotations

from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetLineChanged,
    BudgetProfileUpdated,
    BudgetRemoved,
    BudgetStatusChanged,
    BudgetVersionCreated,
)
from src.core.modules.project_management.application.financials.commitments.commitment_events import (
    CommitmentLineChanged,
    CommitmentMatchChanged,
)
from src.core.modules.project_management.application.financials.configuration.events import (
    CostCodeActivated,
    CostCodeCreated,
    CostCodeDeactivated,
    CostCodeProfileUpdated,
    ProjectCostCodeRestrictionAdded,
    ProjectCostCodeRestrictionRemoved,
    ProjectFinancialProfileCreated,
    ProjectFinancialProfileTransitioned,
    ProjectFinancialProfileUpdated,
)
from src.core.modules.project_management.application.financials.cost.entries.cost_entry_events import (
    CostEntryRecorded,
    CostEntryRemoved,
    CostEntryReversed,
    CostEntryStatusChanged,
    CostEntryUpdated,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastDraftGenerated,
    ForecastLineChanged,
    ForecastVersionChanged,
)
from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    AccountingTransportFinalized,
    BillingPreparationCreated,
    BillingPreparationExternalOutcomeRecorded,
    BillingPreparationLineAdded,
    BillingPreparationLineRemoved,
    BillingPreparationStatusChanged,
    BillingProfileActivated,
    BillingProfileCreated,
    BillingScheduleLineAdded,
    BillingScheduleLineMarkedReady,
)
from src.core.modules.project_management.application.financials.planned_costs.planned_cost_events import (
    PlannedCostSnapshotCalculated,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_events import (
    RateCardCreated,
    RateCardDeactivated,
    RateCardLineAdded,
    RateCardLineDeactivated,
    RateCardLineUpdated,
    RateCardUpdated,
)


def test_budget_and_forecast_events_have_one_shared_handler_per_family(services) -> None:
    bus = services["project_service"]._uow_factory._post_commit_bus
    for event_types, name in (
        (
            (
                ForecastVersionChanged,
                ForecastLineChanged,
                ForecastDraftGenerated,
            ),
            "handle_forecast_event",
        ),
        (
            (
                BudgetVersionCreated,
                BudgetProfileUpdated,
                BudgetLineChanged,
                BudgetStatusChanged,
                BudgetRemoved,
            ),
            "handle_budget_event",
        ),
    ):
        handlers = [
            next(handler for handler in bus._handlers[event_type] if handler.__name__ == name)
            for event_type in event_types
        ]
        assert all(
            sum(handler.__name__ == name for handler in bus._handlers[event_type]) == 1
            for event_type in event_types
        )
        assert all(handler is handlers[0] for handler in handlers)


def test_remaining_finance_events_have_one_handler_per_family(services) -> None:
    bus = services["project_service"]._uow_factory._post_commit_bus
    for event_types, name in (
        ((FinancialChangeChanged,), "handle"),
        ((PlannedCostSnapshotCalculated,), "handle_planned_cost_event"),
        ((CommitmentLineChanged, CommitmentMatchChanged), "handle_commitment_event"),
        (
            (
                CostEntryRecorded,
                CostEntryUpdated,
                CostEntryStatusChanged,
                CostEntryReversed,
                CostEntryRemoved,
            ),
            "handle_cost_entry_event",
        ),
        (
            (
                AccountingTransportFinalized,
                BillingProfileCreated,
                BillingProfileActivated,
                BillingScheduleLineAdded,
                BillingScheduleLineMarkedReady,
                BillingPreparationCreated,
                BillingPreparationLineAdded,
                BillingPreparationLineRemoved,
                BillingPreparationStatusChanged,
                BillingPreparationExternalOutcomeRecorded,
            ),
            "handle_billing_event",
        ),
        (
            (
                ProjectFinancialProfileCreated,
                ProjectFinancialProfileUpdated,
                ProjectFinancialProfileTransitioned,
                CostCodeCreated,
                CostCodeProfileUpdated,
                CostCodeActivated,
                CostCodeDeactivated,
                ProjectCostCodeRestrictionAdded,
                ProjectCostCodeRestrictionRemoved,
            ),
            "handle_financial_profile_event",
        ),
        (
            (
                RateCardCreated,
                RateCardDeactivated,
                RateCardUpdated,
                RateCardLineAdded,
                RateCardLineUpdated,
                RateCardLineDeactivated,
            ),
            "handle_rate_card_event",
        ),
    ):
        handlers = [
            next(handler for handler in bus._handlers[event_type] if handler.__name__ == name)
            for event_type in event_types
        ]
        assert all(
            sum(handler.__name__ == name for handler in bus._handlers[event_type]) == 1
            for event_type in event_types
        )
        assert all(handler is handlers[0] for handler in handlers)
