from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from src.core.modules.project_management.application.common.clock import SystemClock
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
from src.core.modules.project_management.application.financials.governance.command_boundary import (
    FinanceGovernanceOperations,
)
from src.core.modules.project_management.application.financials.invoicing.commands import (
    BillingPreparationSourceCommandHandler,
    BillingPreparationSubmissionCommandHandler,
    PreparationLifecycleCommandHandler,
    ProjectBillingProfileCommandHandler,
    ProjectBillingScheduleCommandHandler,
)
from src.core.modules.project_management.application.financials.invoicing.evidence_builder import (
    BillingPreparationEvidenceBuilder,
)
from src.core.modules.project_management.application.financials.planned_costs.commands import (
    PlannedCostCommandHandler,
)
from src.core.modules.project_management.application.financials.rate_cards.commands import (
    ProjectRateCardCommandHandler,
    RateCardLineCommandHandler,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_resolver import (
    RateCardResolver,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.changes import (
    build_financial_change_schedule_port,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWork,
)
from src.core.platform.application.finance.queries.financial_period_query import (
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.integration.delivery_service import (
    IntegrationOutboxService,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.core.platform.integration.events import IntegrationEventEnvelope
from src.core.shared.events.domain_event import DomainEvent
from src.infra.composition.integration.accounting.accounting_integration import (
    build_accounting_capability,
)


def build_finance_governance_operations_factory(
    platform_services: PlatformServiceBundle, *, clock: SystemClock,
    work_calendar_engine: CalendarProtocol, accounting_adapter_ids: frozenset[str],
) -> Callable[[SqlAlchemyFinanceGovernanceUnitOfWork], FinanceGovernanceOperations]:
    def build_operations(uow: SqlAlchemyFinanceGovernanceUnitOfWork) -> FinanceGovernanceOperations:
        def record_event(event: object) -> None:
            if not isinstance(event, DomainEvent):
                raise TypeError("Finance UoW requires a domain event with occurred_at")
            uow.record_event(event)

        governed_rate_resolver = RateCardResolver(
            reader=SqlAlchemyRateResolutionReader(session=uow._session),
            tenant_context_service=platform_services.tenant_context_service, clock=clock,
        )
        governed_financial_period_queries = FinancialPeriodQueryHandler(
            period_repo=uow.financial_periods, user_session=platform_services.user_session,
        )
        schedule_changes = build_financial_change_schedule_port(
            session=uow._session, user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
            work_calendar_engine=work_calendar_engine,
        )
        handoff_capability = build_accounting_capability(
            session=uow._session, tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session, installed_adapters=accounting_adapter_ids,
        )

        def enqueue_handoff(envelope: IntegrationEventEnvelope, occurred_at: datetime) -> object:
            return IntegrationOutboxService(
                repository=uow.accounting_outbox, owner_module="project_management",
                clock=HandoffRequestClock(occurred_at),
            ).enqueue(envelope)

        budget_lifecycle = BudgetLifecycleCommands(
            session=uow._session,
            budget_repo=uow.budgets,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        budget_lines = BudgetLineCommands(
            session=uow._session,
            budget_repo=uow.budgets,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        budget_approvals = BudgetApprovalCommands(
            session=uow._session,
            budget_repo=uow.budgets,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_commands=platform_services.approval_commands,
            record_event=record_event,
        )
        forecast_lifecycle = ForecastLifecycleCommands(
            session=uow._session,
            forecast_repo=uow.forecasts,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        forecast_lines = ForecastLineCommands(
            session=uow._session,
            forecast_repo=uow.forecasts,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        forecast_approvals = ForecastApprovalCommands(
            session=uow._session,
            forecast_repo=uow.forecasts,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
            approval_commands=platform_services.approval_commands,
        )
        forecast_generation = ForecastGenerationCommands(
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
        financial_changes = FinancialChangeDraftCommandHandler(
            session=uow._session,
            change_repo=uow.changes,
            budget_repo=uow.budgets,
            forecast_repo=uow.forecasts,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            task_service=schedule_changes,
            clock=clock,
            record_event=record_event,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
        )
        financial_change_submissions = FinancialChangeSubmissionCommandHandler(
            session=uow._session,
            change_repo=uow.changes,
            budget_repo=uow.budgets,
            forecast_repo=uow.forecasts,
            task_service=schedule_changes,
            clock=clock,
            approval_repo=uow.approvals,
            record_event=record_event,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
        )
        financial_profiles = FinancialProfileCommandHandler(
            session=uow._session,
            profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        cost_codes = CostCodeCommandHandler(
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
        rate_cards = ProjectRateCardCommandHandler(
            session=uow._session,
            rate_card_repo=uow.rate_cards,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        rate_lines = RateCardLineCommandHandler(
            session=uow._session,
            rate_card_repo=uow.rate_cards,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        planned_costs = PlannedCostCommandHandler(
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
            activity_service=None,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        cost_entries = ProjectCostEntryLifecycleCommandHandler(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            activity_service=None,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        cost_reviews = ProjectCostEntryReviewCommandHandler(
            session=uow._session,
            entry_repo=uow.cost_entries,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            activity_service=None,
            module_catalog_service=platform_services.module_catalog_service,
            approval_commands=platform_services.approval_commands,
            record_event=record_event,
        )
        cost_postings = ProjectCostEntryPostingCommandHandler(
            session=uow._session,
            entry_repo=uow.cost_entries,
            financial_profile_repo=uow.profiles,
            financial_period_queries=governed_financial_period_queries,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            activity_service=None,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=record_event,
        )
        billing_profiles = ProjectBillingProfileCommandHandler(
            session=uow._session,
            billing_repo=uow.billing,
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
            financial_profile_repo=uow.profiles,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        accounting_handoffs = AccountingHandoffRequestCommandHandler(
            session=uow._session,
            billing_repo=uow.billing,
            financial_profile_repo=uow.profiles,
            handoffs=uow.accounting_handoffs,
            enqueue_event=enqueue_handoff,
            evidence_builder=BillingPreparationEvidenceBuilder(user_session=platform_services.user_session),
            capability=handoff_capability,
            context=uow.context,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        billing_preparations = PreparationLifecycleCommandHandler(
            session=uow._session,
            billing_repo=uow.billing,
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
            financial_profile_repo=uow.profiles,
            financial_period_queries=governed_financial_period_queries,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        billing_sources = BillingPreparationSourceCommandHandler(
            session=uow._session,
            billing_repo=uow.billing,
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
            cost_entry_repo=uow.cost_entries,
            labor_posting_repo=uow.labor_postings,
            rate_resolver=governed_rate_resolver,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        billing_submissions = BillingPreparationSubmissionCommandHandler(
            session=uow._session,
            billing_repo=uow.billing,
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
            approval_repo=uow.approvals,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        billing_schedules = ProjectBillingScheduleCommandHandler(
            session=uow._session,
            billing_repo=uow.billing,
            tenant_context_service=platform_services.tenant_context_service,
            clock=clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=record_event,
        )
        return FinanceGovernanceOperations(
            budget_lifecycle=budget_lifecycle,
            budget_lines=budget_lines,
            budget_approvals=budget_approvals,
            forecast_lifecycle=forecast_lifecycle,
            forecast_lines=forecast_lines,
            forecast_approvals=forecast_approvals,
            forecast_generation=forecast_generation,
            financial_changes=financial_changes,
            financial_change_submissions=financial_change_submissions,
            financial_profiles=financial_profiles,
            cost_codes=cost_codes,
            rate_cards=rate_cards,
            rate_lines=rate_lines,
            planned_costs=planned_costs,
            cost_entries=cost_entries,
            cost_reviews=cost_reviews,
            cost_postings=cost_postings,
            billing_profiles=billing_profiles,
            accounting_handoffs=accounting_handoffs,
            billing_preparations=billing_preparations,
            billing_sources=billing_sources,
            billing_submissions=billing_submissions,
            billing_schedules=billing_schedules,
        )

    return build_operations


@dataclass(frozen=True, slots=True)
class HandoffRequestClock:
    """Pin durable enqueue timestamps to the immutable handoff evidence."""

    requested_at: datetime

    def now(self) -> datetime:
        return self.requested_at
