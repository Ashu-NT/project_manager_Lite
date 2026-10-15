from __future__ import annotations

from dataclasses import fields

import pytest

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
from src.core.shared.events.domain_event_context import DomainEventContext
from src.infra.composition.app_container import build_service_dict
from src.infra.integration.approved_time_dispatcher import (
    ApprovedTimeFinancialDispatcher,
)
from src.infra.integration.procurement_financial_dispatcher import (
    ProcurementFinancialDispatcher,
)


def test_budget_and_forecast_events_have_one_shared_handler_per_family(services) -> None:
    bus = services['project_create']._uow_factory._post_commit_bus
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
    bus = services['project_create']._uow_factory._post_commit_bus
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


def test_finance_setup_rate_and_budget_queries_reuse_scoped_repositories(services, session) -> None:
    configuration = services['financial_configuration_query']
    rates = services['rate_card_query']
    budget = services['budget_query']
    assert configuration._profile_repo.session is session
    assert rates._rate_card_repo.session is session
    assert budget._budget_repo.session is session
    assert not hasattr(budget, '_clock')


def test_finance_cost_queries_do_not_own_mutation_or_rate_dependencies(services, session) -> None:
    costs = services['cost_entry_query']
    commitments = services['commitment_query']
    planned = services['planned_cost_query']
    assert costs._entry_repo.session is session
    assert commitments._commitment_repo.session is session
    assert planned._planned_cost_repo.session is session
    assert not hasattr(costs, 'post')
    assert not hasattr(planned, 'calculate_snapshot')


def test_finance_forecast_query_and_generation_have_separate_lifetimes(services, session) -> None:
    query = services['forecast_version_query']
    assert query._forecast_repo.session is session
    boundary = services['finance_governance_commands']
    with boundary._uow_factory.create(context=DomainEventContext(correlation_id='forecast-composition')) as uow:
        operations = boundary._operations_factory(uow)
        assert operations.forecast_generation._session is uow._session
        assert operations.forecast_lifecycle._clock is operations.forecast_generation._clock
        assert uow._session is not session


def test_finance_read_services_preserve_ambient_session(services, session) -> None:
    workspace = services["finance_workspace_query"]
    finance = services["finance_snapshot_query"]

    assert workspace._setup_reader._session is session
    assert workspace._budget_reader._session is session
    assert finance._finance_performance_reader._session is session
    assert finance._finance_snapshot_reader._session is session


def test_finance_worker_dispatchers_share_fresh_session_uow_factory(services, session) -> None:
    approved_time = services["approved_time_financial_dispatcher"]
    procurement = services["procurement_financial_dispatcher"]
    boundary = services["finance_governance_commands"]

    assert approved_time._uow_factory is procurement._uow_factory
    assert approved_time._uow_factory is boundary._uow_factory
    worker_session = approved_time._uow_factory._session_factory()
    try:
        assert worker_session is not session
        assert worker_session.get_bind() is session.get_bind()
    finally:
        worker_session.close()


def test_finance_change_and_billing_queries_reuse_scoped_repositories(services, session) -> None:
    change = services['financial_change_query']
    profile = services['billing_profile_query']
    preparation = services['billing_preparation_query']
    assert change._change_repo.session is session
    assert profile._billing_repo is preparation._billing_repo
    assert preparation._billing_repo.session is session
    assert not hasattr(preparation, '_rate_resolver')


def test_finance_governed_operations_use_one_fresh_session_for_billing_and_rates(services, session) -> None:
    boundary = services['finance_governance_commands']
    with boundary._uow_factory.create(context=DomainEventContext(correlation_id='composition-test')) as uow:
        operations = boundary._operations_factory(uow)
        assert uow._session is not session
        for field in fields(operations):
            assert getattr(operations, field.name)._session is uow._session
        sources = operations.billing_sources
        assert sources._cost_entry_repo is uow.cost_entries
        assert sources._labor_posting_repo is uow.labor_postings
        assert operations.billing_preparations._financial_period_queries._period_repo.session is uow._session
        assert sources._rate_resolver._reader._session is uow._session
        assert operations.planned_costs._rate_resolver is sources._rate_resolver
        assert operations.billing_submissions._approval_repo is uow.approvals
        assert not hasattr(operations.cost_entries, '_rate_resolver')
        with pytest.raises(TypeError, match='requires a domain event'):
            sources._record_event(object())




def test_finance_performance_query_reuses_reporting_baseline_and_reader(services, session) -> None:
    query = services["finance_performance_query"]
    finance = services["finance_snapshot_query"]

    assert query._performance_reader is finance._finance_performance_reader
    assert query._overview_reader._session is session
    assert query._earned_value_authority is services["earned_value_report"]
    assert query._baseline_variance_authority is services['baseline_query']


def test_finance_startup_replays_both_durable_dispatchers_in_order(monkeypatch, session) -> None:
    calls: list[tuple[str, int]] = []
    monkeypatch.setattr(
        ApprovedTimeFinancialDispatcher,
        "dispatch_pending",
        lambda self, *, limit: calls.append(("approved_time", limit)) or 0,
    )
    monkeypatch.setattr(
        ProcurementFinancialDispatcher,
        "dispatch_pending",
        lambda self, *, limit: calls.append(("procurement", limit)) or 0,
    )

    graph = build_service_dict(session)

    assert graph["approved_time_financial_dispatcher"] is not None
    assert graph["procurement_financial_dispatcher"] is not None
    assert calls == [("approved_time", 50), ("procurement", 50)]
