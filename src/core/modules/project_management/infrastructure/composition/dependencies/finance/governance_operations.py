from __future__ import annotations

from collections.abc import Callable

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials import (
    BudgetService,
    FinancialConfigurationService,
    ForecastGenerationService,
    ForecastVersionService,
    PlannedCostService,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProjectCostEntryService,
    ProjectRateCardService,
    RateCardResolver,
)
from src.core.modules.project_management.application.financials.accounting.request_service import (
    AccountingHandoffRequestService,
)
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceOperations,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.financial_change import (
    build_financial_change_approval_deps,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWork,
)
from src.core.platform.application.finance.financial_period_service import (
    FinancialPeriodService,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.shared.events.domain_event import DomainEvent
from src.infra.composition.integration.accounting.accounting_integration import (
    build_accounting_capability,
)
from src.infra.composition.modules.platform_registry import PlatformServiceBundle


def build_finance_governance_operations_factory(
    platform_services: PlatformServiceBundle,
    *,
    clock: SystemClock,
    work_calendar_engine: CalendarProtocol,
    accounting_adapter_ids: frozenset[str],
) -> Callable[[SqlAlchemyFinanceGovernanceUnitOfWork], FinanceGovernanceOperations]:
    def build_operations(
        uow: SqlAlchemyFinanceGovernanceUnitOfWork,
    ) -> FinanceGovernanceOperations:
        def record_event(event: object) -> None:
            if not isinstance(event, DomainEvent):
                raise TypeError("Finance UoW requires a domain event with occurred_at")
            uow.record_event(event)

        governed_rate_resolver = RateCardResolver(
            reader=SqlAlchemyRateResolutionReader(session=uow._session),
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
        )
        governed_financial_period_service = FinancialPeriodService(
            session=uow._session,
            period_repo=uow.financial_periods,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
        )
        budget_operations = BudgetService(
            session=uow._session,
            budget_repo=uow.budgets,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_service=platform_services.approval_service,
            record_event=record_event,
        )
        forecast_version_operations = ForecastVersionService(
            session=uow._session,
            forecast_repo=uow.forecasts,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
            approval_service=platform_services.approval_service,
        )
        forecast_generation_operations = ForecastGenerationService(
            session=uow._session,
            forecast_repo=uow.forecasts,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            planned_cost_repo=uow.planned_costs,
            commitment_repo=uow.commitments,
            cost_entry_repo=uow.cost_entries,
            register_repo=uow.register_entries,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        change_deps = build_financial_change_approval_deps(
            uow._session,
            user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
            work_calendar_engine=work_calendar_engine,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        change_operations = change_deps.financial_change_service
        change_operations._approval_repo = uow.approvals
        change_operations._record_event = record_event
        setup_operations = FinancialConfigurationService(
            session=uow._session,
            profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        rate_card_operations = ProjectRateCardService(
            session=uow._session,
            rate_card_repo=uow.rate_cards,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        planned_cost_operations = PlannedCostService(
            session=uow._session,
            planned_cost_repo=uow.planned_costs,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            assignment_repo=uow.assignments,
            project_resource_repo=uow.project_resources,
            rate_resolver=governed_rate_resolver,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        cost_entry_operations = ProjectCostEntryService(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_service=governed_financial_period_service,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_service=platform_services.approval_service,
            rate_resolver=governed_rate_resolver,
            labor_posting_repo=uow.labor_postings,
            record_event=record_event,
        )
        billing_profile_operations = ProjectBillingProfileService(
            session=uow._session,
            billing_repo=uow.billing,
            financial_profile_repo=uow.profiles,
            project_repo=uow.projects,
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        billing_preparation_operations = ProjectBillingPreparationService(
            session=uow._session,
            billing_repo=uow.billing,
            financial_profile_repo=uow.profiles,
            cost_entry_repo=uow.cost_entries,
            labor_posting_repo=uow.labor_postings,
            rate_resolver=governed_rate_resolver,
            financial_period_service=governed_financial_period_service,
            approval_service=platform_services.approval_service,
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        billing_preparation_operations._approval_repo = uow.approvals
        billing_preparation_operations._handoff_request_service = AccountingHandoffRequestService(
            preparations=billing_preparation_operations,
            handoffs=uow.accounting_handoffs,
            outbox=uow.accounting_outbox,
            context=uow.context,
            capability=build_accounting_capability(
                session=uow._session,
                tenant_context_service=platform_services.tenant_context_service,
                user_session=platform_services.user_session,
                installed_adapters=accounting_adapter_ids,
            ),
        )
        return FinanceGovernanceOperations(
            budgets=budget_operations,
            forecast_versions=forecast_version_operations,
            forecast_generation=forecast_generation_operations,
            financial_changes=change_operations,
            financial_setup=setup_operations,
            rate_cards=rate_card_operations,
            planned_costs=planned_cost_operations,
            cost_entries=cost_entry_operations,
            billing_profiles=billing_profile_operations,
            billing_preparations=billing_preparation_operations,
        )

    return build_operations
