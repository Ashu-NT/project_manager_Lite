from __future__ import annotations

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
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.governed_ports import (
    FINANCE_MUTATIONS,
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


def test_finance_setup_rate_and_budget_preserve_raw_service_lifetimes(services, session) -> None:
    configuration = services["financial_configuration_service"]
    rate_cards = services["rate_card_service"]
    budget = services["budget_service"]
    resolver = services["rate_card_resolver"]

    assert configuration._read_service._session is session
    assert rate_cards._read_service._session is session
    assert budget._read_service._session is session
    assert budget._read_service._clock is resolver._clock
    assert resolver._clock is services["resource_service"]._clock


def test_finance_cost_services_preserve_session_clock_and_rate_resolver(services, session) -> None:
    cost_entries = services["cost_entry_service"]._read_service
    commitments = services["commitment_service"]
    planned_costs = services["planned_cost_service"]._read_service
    resolver = services["rate_card_resolver"]

    assert cost_entries._session is session
    assert commitments._session is session
    assert planned_costs._session is session
    assert cost_entries._clock is commitments._clock is planned_costs._clock
    assert cost_entries._clock is resolver._clock
    assert cost_entries._rate_resolver is planned_costs._rate_resolver is resolver


def test_finance_forecast_services_preserve_session_and_clock(services, session) -> None:
    version = services["forecast_version_service"]._read_service
    generation = services["forecast_generation_service"]._read_service

    assert version._session is session
    assert generation._session is session
    assert version._clock is generation._clock is services["rate_card_resolver"]._clock


def test_finance_read_services_preserve_ambient_session(services, session) -> None:
    workspace = services["finance_workspace_query"]
    finance = services["finance_service"]

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


def test_finance_change_and_billing_preserve_raw_service_dependencies(services, session) -> None:
    change = services["financial_change_service"]._read_service
    profile = services["billing_profile_service"]._read_service
    preparation = services["billing_preparation_service"]._read_service
    resolver = services["rate_card_resolver"]

    assert change._session is profile._session is preparation._session is session
    assert change._clock is profile._clock is preparation._clock is resolver._clock
    assert preparation._rate_resolver is resolver


def test_finance_governed_operations_use_one_fresh_session_for_billing_and_rates(
    services, session
) -> None:
    boundary = services["finance_governance_commands"]
    uow = boundary._uow_factory.create(context=DomainEventContext(correlation_id="composition-test"))
    try:
        operations = boundary._operations_factory(uow)
        assert uow._session is not session
        for service in (
            operations.budgets,
            operations.forecast_versions,
            operations.forecast_generation,
            operations.financial_setup,
            operations.rate_cards,
            operations.planned_costs,
            operations.cost_entries,
            operations.billing_profiles,
            operations.billing_preparations,
        ):
            assert service._session is uow._session

        billing = operations.billing_preparations
        assert billing._cost_entry_repo is uow.cost_entries
        assert billing._labor_posting_repo is uow.labor_postings
        assert billing._financial_period_service._session is uow._session
        assert billing._rate_resolver._reader._session is uow._session
        assert operations.planned_costs._rate_resolver is billing._rate_resolver
        assert operations.cost_entries._rate_resolver is billing._rate_resolver
        assert billing._approval_repo is uow.approvals
        with pytest.raises(TypeError, match="requires a domain event"):
            billing._record_event(object())
    finally:
        uow._session.close()


def test_finance_governed_ports_share_one_boundary_and_declared_mutations(services) -> None:
    boundary = services["finance_governance_commands"]
    families = {
        "financial_setup": "financial_configuration_service",
        "budget": "budget_service",
        "forecast_version": "forecast_version_service",
        "forecast_generation": "forecast_generation_service",
        "financial_change": "financial_change_service",
        "rate_card": "rate_card_service",
        "planned_cost": "planned_cost_service",
        "cost_entry": "cost_entry_service",
        "billing_profile": "billing_profile_service",
        "billing_preparation": "billing_preparation_service",
    }
    assert set(families) == set(FINANCE_MUTATIONS)
    for family, service_key in families.items():
        port = services[service_key]
        assert port._boundary is boundary
        assert port._family == family
        assert port._mutations == FINANCE_MUTATIONS[family]


def test_finance_performance_query_reuses_reporting_baseline_and_reader(services, session) -> None:
    query = services["finance_performance_query"]
    finance = services["finance_service"]

    assert query._performance_reader is finance._finance_performance_reader
    assert query._overview_reader._session is session
    assert query._earned_value_authority is services["reporting_service"]
    assert query._baseline_variance_authority is services["baseline_service"]


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
