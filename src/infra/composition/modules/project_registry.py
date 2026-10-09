from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.collaboration import (
    CollaborationService,
)
from src.core.modules.project_management.application.collaboration.collaboration_events import (
    TaskCommentChanged,
    TaskCommentReactionChanged,
    TaskCommentReadStateChanged,
)
from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    build_task_comment_view_invalidation_handler,
)
from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import (
    ApprovedTimeLaborCostConsumer,
    BudgetService,
    FinanceService,
    FinancialChangeService,
    FinancialConfigurationService,
    ForecastGenerationService,
    ForecastVersionService,
    PlannedCostService,
    ProcurementFinancialConsumer,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProjectCommitmentService,
    ProjectCostEntryService,
    ProjectFinancePerformanceQuery,
    ProjectFinanceWorkspaceQuery,
    ProjectRateCardService,
    RateCardResolver,
)
from src.core.modules.project_management.application.financials.budgets.budget_events import (
    BudgetLineChanged,
    BudgetProfileUpdated,
    BudgetRemoved,
    BudgetStatusChanged,
    BudgetVersionCreated,
)
from src.core.modules.project_management.application.financials.budgets.event_handlers.view_invalidation import (
    build_budget_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.commitments.commitment_events import (
    CommitmentLineChanged,
    CommitmentMatchChanged,
)
from src.core.modules.project_management.application.financials.commitments.event_handlers.view_invalidation import (
    build_commitment_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.configuration.event_handlers.view_invalidation import (
    build_financial_profile_view_invalidation_handler,
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
from src.core.modules.project_management.application.financials.cost.entries.event_handlers.view_invalidation import (
    build_cost_entry_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.financial_changes.event_handlers.view_invalidation import (
    build_financial_change_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
)
from src.core.modules.project_management.application.financials.forecasts.event_handlers.view_invalidation import (
    build_forecast_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastDraftGenerated,
    ForecastLineChanged,
    ForecastVersionChanged,
)
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernanceOperations,
    FinanceGovernedServicePort,
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
from src.core.modules.project_management.application.financials.invoicing.event_handlers.view_invalidation import (
    build_billing_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.planned_costs.event_handlers.view_invalidation import (
    build_planned_cost_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.planned_costs.planned_cost_events import (
    PlannedCostSnapshotCalculated,
)
from src.core.modules.project_management.application.financials.rate_cards.event_handlers.view_invalidation import (
    build_rate_card_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_events import (
    RateCardCreated,
    RateCardDeactivated,
    RateCardLineAdded,
    RateCardLineDeactivated,
    RateCardLineUpdated,
    RateCardUpdated,
)
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.portfolio.event_handlers.view_invalidation import (
    build_portfolio_view_invalidation_handler,
)
from src.core.modules.project_management.application.portfolio.portfolio_events import (
    PortfolioIntakeItemChanged,
    PortfolioProjectDependencyChanged,
    PortfolioScenarioChanged,
    PortfolioScoringTemplateChanged,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.reporting import (
    ReportingService,
)
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.resources.capacity.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.resources.capacity.resource_capacity_calculator import (
    ResourceCapacityCalculator,
)
from src.core.modules.project_management.application.resources.capacity.resource_workload_service import (
    ResourceWorkloadService,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.resources.portfolio.resource_pool_service import (
    PortfolioResourcePoolService,
)
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import (
    ProjectCalendarAdapter,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.infrastructure.composition.dependencies.projects import (
    build_project_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.register import (
    build_register_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.resources import (
    build_resource_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.scheduling import (
    build_baseline_service,
    build_scheduling_foundation,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.tasks import (
    build_task_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.timesheets import (
    build_timesheet_service,
)
from src.core.modules.project_management.infrastructure.composition.events.projects import (
    register_project_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.register import (
    register_register_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.resources import (
    register_resource_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.scheduling import (
    register_baseline_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.tasks import (
    register_task_events,
)
from src.core.modules.project_management.infrastructure.composition.events.timesheets import (
    register_timesheet_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.registrations.access import (
    register_project_scope_access,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.financial_change import (
    build_financial_change_approval_deps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.handlers import (
    register_project_management_approval_handlers,
)
from src.core.modules.project_management.infrastructure.importers import (
    DataImportService,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration import (
    SqlAlchemyCollaborationWorkspaceReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyEvmSeriesReader,
    SqlAlchemyFinanceBillingReader,
    SqlAlchemyFinanceBudgetReader,
    SqlAlchemyFinanceChangeReader,
    SqlAlchemyFinanceForecastReader,
    SqlAlchemyFinanceIntegrationReader,
    SqlAlchemyFinanceLookupReader,
    SqlAlchemyFinancePerformanceReader,
    SqlAlchemyFinancePlannedCostReader,
    SqlAlchemyFinanceRateReader,
    SqlAlchemyFinanceSetupReader,
    SqlAlchemyFinanceSnapshotReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.portfolio import (
    SqlAlchemyPortfolioHeatmapReader,
    SqlAlchemyPortfolioResourcePoolReader,
    SqlAlchemyPortfolioScenarioReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.projects import (
    SqlAlchemyProjectCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceWorkloadDemandReader,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.collaboration.collaboration_unit_of_work import (
    SqlAlchemyCollaborationUnitOfWorkFactory,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWork,
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.modules.project_management.infrastructure.persistence.uow.portfolio.portfolio_unit_of_work import (
    SqlAlchemyPortfolioUnitOfWorkFactory,
)
from src.core.platform.application.finance.financial_period_service import (
    FinancialPeriodService,
)
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.time_management.time import TimeService
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.domain.security.identity.service_principal import (
    ServicePrincipal,
)
from src.infra.composition.modules.platform_registry import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkFactoryBase

logger = logging.getLogger(__name__)


def _prepare_finance_command_session(session: Session) -> None:
    """Release a retained SQLite transaction before opening a fresh Finance UoW."""
    bind = session.get_bind()
    if bind.dialect.name != "sqlite" or not session.in_transaction():
        return
    logger.debug("Releasing shared SQLite session transaction before Finance command")
    session.rollback()


@dataclass(frozen=True)
class ProjectManagementServiceBundle:
    time_service: TimeService
    collaboration_service: CollaborationService
    project_service: ProjectService
    task_service: TaskService
    timesheet_service: TimesheetService
    resource_service: ResourceService
    finance_governance_commands: FinanceGovernanceCommandBoundary
    financial_configuration_service: FinancialConfigurationService
    forecast_generation_service: ForecastGenerationService
    forecast_version_service: ForecastVersionService
    financial_change_service: FinancialChangeService
    billing_profile_service: ProjectBillingProfileService
    billing_preparation_service: ProjectBillingPreparationService
    rate_card_service: ProjectRateCardService
    rate_card_resolver: RateCardResolver
    budget_service: BudgetService
    cost_entry_service: ProjectCostEntryService
    finance_worker_uow_factory: SqlAlchemyFinanceGovernanceUnitOfWorkFactory
    approved_time_consumer_factory: Callable[
        [SqlAlchemyFinanceGovernanceUnitOfWork, ServicePrincipal],
        ApprovedTimeLaborCostConsumer,
    ]
    procurement_consumer_factory: Callable[
        [SqlAlchemyFinanceGovernanceUnitOfWork, ServicePrincipal],
        ProcurementFinancialConsumer,
    ]
    commitment_service: ProjectCommitmentService
    planned_cost_service: PlannedCostService
    finance_workspace_query: ProjectFinanceWorkspaceQuery
    finance_performance_query: ProjectFinancePerformanceQuery
    finance_service: FinanceService
    work_calendar_engine: CalendarProtocol  # GlobalCalendarShim — enterprise-backed
    scheduling_engine: SchedulingEngine
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    portfolio_service: PortfolioService
    register_service: RegisterService
    project_resource_service: ProjectResourceService
    data_import_service: DataImportService
    assignment_skill_validator: AssignmentSkillValidator
    project_calendar_adapter: ProjectCalendarAdapter
    enterprise_resource_availability: EnterpriseResourceAvailabilityService
    resource_capacity_calculator: ResourceCapacityCalculator
    resource_workload_service: ResourceWorkloadService
    portfolio_resource_pool_service: PortfolioResourcePoolService


def build_project_management_service_bundle(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    approved_time_outbox_service: IntegrationOutboxService | None = None,
    accounting_adapter_ids: frozenset[str] = frozenset(),
) -> ProjectManagementServiceBundle:
    started = perf_counter()
    logger.debug("Project Management service bundle build begin")
    logger.debug("Project Management platform registrations begin")
    register_project_scope_access(repositories, platform_services)
    logger.debug("Project Management platform registrations complete")
    logger.debug("Project Management core services build begin")
    # GlobalCalendarShim is the enterprise-backed calendar. Used everywhere WorkCalendarEngine was.
    work_calendar_engine = platform_services.global_calendar_shim
    shared_session_uow_factory = SqlAlchemyUnitOfWorkFactoryBase(
        session_factory=lambda: session,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
    )
    register_project_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    project_service = build_project_service(
        session,
        repositories,
        platform_services,
        shared_session_uow_factory,
    )

    timesheet_service = build_timesheet_service(
        session,
        repositories,
        platform_services,
        approved_time_outbox_service=approved_time_outbox_service,
    )
    time_service: TimeService = timesheet_service
    register_timesheet_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    project_resource_service = ProjectResourceService(
        project_resource_repo=repositories.project_resource_repo,
        resource_repo=repositories.resource_repo,
        project_repo=repositories.project_repo,
        session=session,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        task_repo=repositories.task_repo,
        assignment_repo=repositories.assignment_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        shared_uow_factory=shared_session_uow_factory,
    )
    register_register_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_service = build_register_service(session, repositories, platform_services)
    _pre_project_calendar_adapter, scheduling_engine = build_scheduling_foundation(
        session,
        repositories,
        platform_services,
    )
    logger.debug("Project Management scheduling foundation built")
    assignment_skill_validator = AssignmentSkillValidator(
        skill_repo=repositories.resource_skill_repo,
        cert_repo=repositories.resource_cert_repo,
        requirement_repo=repositories.task_skill_req_repo,
    )
    enterprise_resource_availability = EnterpriseResourceAvailabilityService(
        resolver=platform_services.platform_calendar_resolver,
        resource_repo=repositories.resource_repo,
    )
    register_task_events(
        platform_services.platform_transactional_dispatcher,
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    task_service = build_task_service(
        session,
        repositories,
        platform_services,
        timesheet_service=timesheet_service,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        assignment_skill_validator=assignment_skill_validator,
        enterprise_resource_availability=enterprise_resource_availability,
    )
    # The resolver owns the effective-time source for immutable rate snapshots.
    system_clock = SystemClock()
    register_resource_view_invalidation(
        session,
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    resource_service = build_resource_service(
        session,
        repositories,
        platform_services,
        clock=system_clock,
    )
    financial_configuration_service = FinancialConfigurationService(
        session=session,
        profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        project_repo=repositories.project_repo,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    rate_card_service = ProjectRateCardService(
        session=session,
        rate_card_repo=repositories.project_rate_card_repo,
        project_repo=repositories.project_repo,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    rate_resolution_reader = SqlAlchemyRateResolutionReader(session=session)
    rate_card_resolver = RateCardResolver(
        reader=rate_resolution_reader,
        tenant_context_service=platform_services.tenant_context_service,
        clock=system_clock,
    )
    budget_service = BudgetService(
        session=session,
        budget_repo=repositories.project_budget_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        approval_service=platform_services.approval_service,
    )
    cost_entry_service = ProjectCostEntryService(
        session=session,
        entry_repo=repositories.project_cost_entry_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        financial_period_service=platform_services.financial_period_service,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        approval_service=platform_services.approval_service,
        rate_resolver=rate_card_resolver,
        labor_posting_repo=repositories.approved_time_labor_posting_repo,
    )
    commitment_service = ProjectCommitmentService(
        session=session,
        commitment_repo=repositories.project_commitment_repo,
        cost_entry_repo=repositories.project_cost_entry_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        party_repo=repositories.party_repo,
        site_repo=repositories.site_repo,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    planned_cost_service = PlannedCostService(
        session=session,
        planned_cost_repo=repositories.planned_cost_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        assignment_repo=repositories.assignment_repo,
        project_resource_repo=repositories.project_resource_repo,
        rate_resolver=rate_card_resolver,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    from src.core.modules.project_management.application.financials.accounting.request_service import (
        AccountingHandoffRequestService,
    )
    from src.infra.composition.integration.accounting.accounting_integration import (
        build_accounting_capability,
    )

    finance_workspace_query = ProjectFinanceWorkspaceQuery(
        accounting_capability=build_accounting_capability(
            session=session, tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session, installed_adapters=accounting_adapter_ids,
        ),
        setup_reader=SqlAlchemyFinanceSetupReader(session=session),
        lookup_reader=SqlAlchemyFinanceLookupReader(session=session),
        budget_reader=SqlAlchemyFinanceBudgetReader(session=session),
        planned_cost_reader=SqlAlchemyFinancePlannedCostReader(session=session),
        forecast_reader=SqlAlchemyFinanceForecastReader(session=session),
        rate_reader=SqlAlchemyFinanceRateReader(session=session),
        change_reader=SqlAlchemyFinanceChangeReader(session=session),
        billing_reader=SqlAlchemyFinanceBillingReader(session=session),
        integration_reader=SqlAlchemyFinanceIntegrationReader(session=session),
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    reporting_service = ReportingService(
        project_repo=repositories.project_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        assignment_repo=repositories.assignment_repo,
        scheduling_engine=scheduling_engine,
        calendar=platform_services.global_calendar_shim,
        baseline_repo=repositories.baseline_repo,
        project_resource_repo=repositories.project_resource_repo,
        rate_resolver=rate_card_resolver,
        tenant_context_service=platform_services.tenant_context_service,
        evm_series_reader=SqlAlchemyEvmSeriesReader(session=session),
        finance_snapshot_reader=SqlAlchemyFinanceSnapshotReader(session=session),
        financial_profile_repo=repositories.project_financial_profile_repo,
        billing_repo=repositories.project_billing_repo,
        billing_reader=SqlAlchemyFinanceBillingReader(session=session),
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    finance_performance_reader = SqlAlchemyFinancePerformanceReader(
        session=session,
        calendar=platform_services.global_calendar_shim,
    )
    finance_service = FinanceService(
        rate_resolver=rate_card_resolver,
        finance_snapshot_reader=SqlAlchemyFinanceSnapshotReader(session=session),
        finance_performance_reader=finance_performance_reader,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    forecast_version_service = ForecastVersionService(
        session=session,
        forecast_repo=repositories.project_forecast_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    forecast_generation_service = ForecastGenerationService(
        session=session,
        forecast_repo=repositories.project_forecast_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        planned_cost_repo=repositories.planned_cost_repo,
        commitment_repo=repositories.project_commitment_repo,
        cost_entry_repo=repositories.project_cost_entry_repo,
        register_repo=repositories.register_repo,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )

    finance_governance_uow_session_factory = sessionmaker(
        bind=platform_services.session.bind, future=True
    )
    finance_governance_uow_factory = SqlAlchemyFinanceGovernanceUnitOfWorkFactory(
        session_factory=finance_governance_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )

    def build_approved_time_consumer(
        uow: SqlAlchemyFinanceGovernanceUnitOfWork,
        principal: ServicePrincipal,
    ) -> ApprovedTimeLaborCostConsumer:
        worker_rate_resolver = RateCardResolver(
            reader=SqlAlchemyRateResolutionReader(session=uow._session),
            tenant_context_service=platform_services.tenant_context_service,
            clock=system_clock,
        )
        worker_cost_service = ProjectCostEntryService(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_service=FinancialPeriodService(
                session=uow._session,
                period_repo=uow.financial_periods,
                tenant_context_service=platform_services.tenant_context_service,
                user_session=platform_services.user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
            ),
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_service=platform_services.approval_service,
            rate_resolver=worker_rate_resolver,
            labor_posting_repo=uow.labor_postings,
        )
        return ApprovedTimeLaborCostConsumer(
            worker_cost_service,
            service_principal=principal,
        )

    def build_procurement_consumer(
        uow: SqlAlchemyFinanceGovernanceUnitOfWork,
        principal: ServicePrincipal,
    ) -> ProcurementFinancialConsumer:
        worker_rate_resolver = RateCardResolver(
            reader=SqlAlchemyRateResolutionReader(session=uow._session),
            tenant_context_service=platform_services.tenant_context_service,
            clock=system_clock,
        )
        worker_cost_service = ProjectCostEntryService(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_service=FinancialPeriodService(
                session=uow._session,
                period_repo=uow.financial_periods,
                tenant_context_service=platform_services.tenant_context_service,
                user_session=platform_services.user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
            ),
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_service=platform_services.approval_service,
            rate_resolver=worker_rate_resolver,
            labor_posting_repo=uow.labor_postings,
        )
        worker_commitment_service = ProjectCommitmentService(
            session=uow._session,
            commitment_repo=uow.commitments,
            cost_entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            party_repo=uow.parties,
            site_repo=uow.sites,
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
        )
        return ProcurementFinancialConsumer(
            commitment_service=worker_commitment_service,
            cost_entry_service=worker_cost_service,
            task_repo=uow.tasks,
            service_principal=principal,
        )
    _forecast_view_invalidation_handler = build_forecast_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _forecast_event_type in (ForecastVersionChanged, ForecastLineChanged, ForecastDraftGenerated):
        platform_services.platform_post_commit_bus.subscribe(
            _forecast_event_type, _forecast_view_invalidation_handler
        )
    _financial_change_view_invalidation_handler = (
        build_financial_change_view_invalidation_handler(
            platform_services.platform_view_invalidation_channel
        )
    )
    platform_services.platform_post_commit_bus.subscribe(
        FinancialChangeChanged, _financial_change_view_invalidation_handler
    )
    _planned_cost_view_invalidation_handler = build_planned_cost_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    platform_services.platform_post_commit_bus.subscribe(
        PlannedCostSnapshotCalculated, _planned_cost_view_invalidation_handler
    )
    _commitment_view_invalidation_handler = build_commitment_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _commitment_event_type in (CommitmentLineChanged, CommitmentMatchChanged):
        platform_services.platform_post_commit_bus.subscribe(
            _commitment_event_type, _commitment_view_invalidation_handler
        )
    _cost_entry_view_invalidation_handler = build_cost_entry_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _cost_entry_event_type in (
        CostEntryRecorded,
        CostEntryUpdated,
        CostEntryStatusChanged,
        CostEntryReversed,
        CostEntryRemoved,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _cost_entry_event_type, _cost_entry_view_invalidation_handler
        )
    _budget_view_invalidation_handler = build_budget_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _budget_event_type in (
        BudgetVersionCreated,
        BudgetProfileUpdated,
        BudgetLineChanged,
        BudgetStatusChanged,
        BudgetRemoved,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _budget_event_type, _budget_view_invalidation_handler
        )
    _billing_view_invalidation_handler = build_billing_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _billing_event_type in (
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
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _billing_event_type, _billing_view_invalidation_handler
        )
    _financial_profile_view_invalidation_handler = build_financial_profile_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _financial_profile_event_type in (
        ProjectFinancialProfileCreated,
        ProjectFinancialProfileUpdated,
        ProjectFinancialProfileTransitioned,
        CostCodeCreated,
        CostCodeProfileUpdated,
        CostCodeActivated,
        CostCodeDeactivated,
        ProjectCostCodeRestrictionAdded,
        ProjectCostCodeRestrictionRemoved,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _financial_profile_event_type, _financial_profile_view_invalidation_handler
        )
    _rate_card_view_invalidation_handler = build_rate_card_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _rate_card_event_type in (
        RateCardCreated,
        RateCardDeactivated,
        RateCardUpdated,
        RateCardLineAdded,
        RateCardLineUpdated,
        RateCardLineDeactivated,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _rate_card_event_type, _rate_card_view_invalidation_handler
        )
    financial_change_service = FinancialChangeService(
        session=session,
        change_repo=repositories.financial_change_repo,
        budget_repo=repositories.project_budget_repo,
        forecast_repo=repositories.project_forecast_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        task_service=task_service,
        approval_service=platform_services.approval_service,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )

    def build_finance_governance_operations(uow):
        budget_operations = BudgetService(
            session=uow._session,
            budget_repo=uow.budgets,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_service=platform_services.approval_service,
            record_event=uow.record_event,
        )
        forecast_version_operations = ForecastVersionService(
            session=uow._session,
            forecast_repo=uow.forecasts,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=uow.record_event,
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
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=uow.record_event,
        )
        change_deps = build_financial_change_approval_deps(
            uow._session,
            user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
            work_calendar_engine=work_calendar_engine,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=uow.record_event,
        )
        change_operations = change_deps.financial_change_service
        change_operations._approval_repo = uow.approvals
        change_operations._record_event = uow.record_event
        setup_operations = FinancialConfigurationService(
            session=uow._session,
            profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=uow.record_event,
        )
        rate_card_operations = ProjectRateCardService(
            session=uow._session,
            rate_card_repo=uow.rate_cards,
            project_repo=uow.projects,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=uow.record_event,
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
            rate_resolver=rate_card_resolver,
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=uow.record_event,
        )
        cost_entry_operations = ProjectCostEntryService(
            session=uow._session,
            entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            resource_repo=uow.resources,
            financial_period_service=FinancialPeriodService(
                session=uow._session,
                period_repo=uow.financial_periods,
                tenant_context_service=platform_services.tenant_context_service,
                user_session=platform_services.user_session,
                enterprise_audit_service=uow._enterprise_audit_service,
            ),
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            approval_service=platform_services.approval_service,
            rate_resolver=rate_card_resolver,
            labor_posting_repo=uow.labor_postings,
            record_event=uow.record_event,
        )
        billing_profile_operations = ProjectBillingProfileService(
            session=uow._session,
            billing_repo=uow.billing,
            financial_profile_repo=uow.profiles,
            project_repo=uow.projects,
            tenant_context_service=platform_services.tenant_context_service,
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=uow.record_event,
        )
        billing_preparation_operations = ProjectBillingPreparationService(
            session=uow._session,
            billing_repo=uow.billing,
            financial_profile_repo=uow.profiles,
            cost_entry_repo=repositories.project_cost_entry_repo,
            labor_posting_repo=repositories.approved_time_labor_posting_repo,
            rate_resolver=rate_card_resolver,
            financial_period_service=platform_services.financial_period_service,
            approval_service=platform_services.approval_service,
            tenant_context_service=platform_services.tenant_context_service,
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            record_event=uow.record_event,
        )
        billing_preparation_operations._approval_repo = uow.approvals
        billing_preparation_operations._handoff_request_service = AccountingHandoffRequestService(
            preparations=billing_preparation_operations, handoffs=uow.accounting_handoffs,
            outbox=uow.accounting_outbox, context=uow.context,
            capability=build_accounting_capability(
                session=uow._session, tenant_context_service=platform_services.tenant_context_service,
                user_session=platform_services.user_session, installed_adapters=accounting_adapter_ids,
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

    finance_governance_commands = FinanceGovernanceCommandBoundary(
        uow_factory=finance_governance_uow_factory,
        operations_factory=build_finance_governance_operations,
        prepare_command=lambda: _prepare_finance_command_session(session),
    )
    financial_configuration_service = FinanceGovernedServicePort(
        read_service=financial_configuration_service,
        boundary=finance_governance_commands,
        family="financial_setup",
        mutations=frozenset(
            {
                "configure_profile",
                "transition_profile",
                "create_cost_code",
                "update_cost_code",
                "deactivate_cost_code",
                "activate_cost_code",
                "add_project_cost_code",
                "remove_project_cost_code",
            }
        ),
    )
    budget_service = FinanceGovernedServicePort(
        read_service=budget_service,
        boundary=finance_governance_commands,
        family="budget",
        mutations=frozenset(
            {
                "create_budget",
                "create_successor",
                "request_budget_approval",
                "submit_budget",
                "approve_budget",
                "reject_budget",
                "close_budget",
                "update_budget_header",
                "delete_budget",
                "add_line",
                "update_line",
                "delete_line",
            }
        ),
    )
    forecast_version_service = FinanceGovernedServicePort(
        read_service=forecast_version_service,
        boundary=finance_governance_commands,
        family="forecast_version",
        mutations=frozenset(
            {
                "create_forecast",
                "add_line",
                "update_line",
                "delete_line",
                "submit_forecast",
                "request_forecast_approval",
                "approve_forecast",
                "reject_forecast",
                "delete_forecast",
            }
        ),
    )
    forecast_generation_service = FinanceGovernedServicePort(
        read_service=forecast_generation_service,
        boundary=finance_governance_commands,
        family="forecast_generation",
        mutations=frozenset({"generate_draft"}),
    )
    financial_change_service = FinanceGovernedServicePort(
        read_service=financial_change_service,
        boundary=finance_governance_commands,
        family="financial_change",
        mutations=frozenset(
            {
                "create_change",
                "update_change",
                "add_impact",
                "update_impact",
                "remove_impact",
                "submit_change",
            }
        ),
    )
    rate_card_service = FinanceGovernedServicePort(
        read_service=rate_card_service,
        boundary=finance_governance_commands,
        family="rate_card",
        mutations=frozenset(
            {
                "create_rate_card",
                "update_rate_card",
                "deactivate_rate_card",
                "create_line",
                "update_line",
                "deactivate_line",
            }
        ),
    )
    planned_cost_service = FinanceGovernedServicePort(
        read_service=planned_cost_service,
        boundary=finance_governance_commands,
        family="planned_cost",
        mutations=frozenset({"calculate_snapshot"}),
    )
    cost_entry_service = FinanceGovernedServicePort(
        read_service=cost_entry_service,
        boundary=finance_governance_commands,
        family="cost_entry",
        mutations=frozenset(
            {
                "create_manual_entry",
                "update_draft",
                "delete_draft",
                "submit",
                "approve",
                "reject",
                "post",
                "reverse",
            }
        ),
    )
    billing_profile_service = ProjectBillingProfileService(
        session=session,
        billing_repo=repositories.project_billing_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        project_repo=repositories.project_repo,
        tenant_context_service=platform_services.tenant_context_service,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
    )
    billing_preparation_service = ProjectBillingPreparationService(
        session=session,
        billing_repo=repositories.project_billing_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_entry_repo=repositories.project_cost_entry_repo,
        labor_posting_repo=repositories.approved_time_labor_posting_repo,
        rate_resolver=rate_card_resolver,
        financial_period_service=platform_services.financial_period_service,
        approval_service=platform_services.approval_service,
        tenant_context_service=platform_services.tenant_context_service,
        clock=system_clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
    )
    billing_profile_service = FinanceGovernedServicePort(
        read_service=billing_profile_service,
        boundary=finance_governance_commands,
        family="billing_profile",
        mutations=frozenset(
            {
                "create_profile",
                "activate_profile",
                "add_schedule_line",
                "mark_schedule_line_ready",
            }
        ),
    )
    billing_preparation_service = FinanceGovernedServicePort(
        read_service=billing_preparation_service,
        boundary=finance_governance_commands,
        family="billing_preparation",
        mutations=frozenset(
            {
                "create_preparation",
                "add_fixed_price_source",
                "add_approved_time_source",
                "add_cost_plus_source",
                "remove_draft_line",
                "cancel_draft_preparation",
                "submit_preparation",
                "request_delivery",
            }
        ),
    )
    collaboration_uow_session_factory = sessionmaker(bind=platform_services.session.bind, future=True)
    collaboration_uow_factory = SqlAlchemyCollaborationUnitOfWorkFactory(
        session_factory=collaboration_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    _task_comment_view_invalidation_handler = build_task_comment_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _task_comment_event_type in (
        TaskCommentChanged,
        TaskCommentReactionChanged,
        TaskCommentReadStateChanged,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _task_comment_event_type, _task_comment_view_invalidation_handler
        )
    from src.core.modules.project_management.infrastructure.collaboration_attachments import (
        cleanup_task_comment_attachments,
        store_task_comment_attachments,
    )

    collaboration_service = CollaborationService(
        session=session,
        comment_repo=repositories.task_comment_repo,
        presence_repo=repositories.task_presence_repo,
        task_repo=repositories.task_repo,
        project_repo=repositories.project_repo,
        user_repo=repositories.user_repo,
        workspace_reader=SqlAlchemyCollaborationWorkspaceReader(session=session),
        document_integration_service=platform_services.document_integration_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
        view_invalidation_channel=platform_services.platform_view_invalidation_channel,
        uow_factory=collaboration_uow_factory,
        attachment_store=store_task_comment_attachments,
        attachment_cleanup=cleanup_task_comment_attachments,
        clock=SystemClock(),
    )
    portfolio_uow_session_factory = sessionmaker(bind=platform_services.session.bind, future=True)
    portfolio_uow_factory = SqlAlchemyPortfolioUnitOfWorkFactory(
        session_factory=portfolio_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    _portfolio_view_invalidation_handler = build_portfolio_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _portfolio_event_type in (
        PortfolioIntakeItemChanged,
        PortfolioScenarioChanged,
        PortfolioScoringTemplateChanged,
        PortfolioProjectDependencyChanged,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _portfolio_event_type,
            _portfolio_view_invalidation_handler,
        )
    portfolio_service = PortfolioService(
        session=session,
        intake_repo=repositories.portfolio_intake_repo,
        dependency_repo=repositories.portfolio_project_dependency_repo,
        scoring_template_repo=repositories.portfolio_scoring_template_repo,
        scenario_repo=repositories.portfolio_scenario_repo,
        audit_repo=repositories.audit_entry_repo,
        project_repo=repositories.project_repo,
        heatmap_reader=SqlAlchemyPortfolioHeatmapReader(session=session),
        scenario_reader=SqlAlchemyPortfolioScenarioReader(session=session),
        calendar=platform_services.global_calendar_shim,
        project_calendar_adapter=_pre_project_calendar_adapter,
        rate_resolver=rate_card_resolver,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        project_catalog_reader=SqlAlchemyProjectCatalogReader(session=session),
        uow_factory=portfolio_uow_factory,
    )
    register_baseline_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    baseline_service = build_baseline_service(
        session,
        repositories,
        platform_services,
        scheduling_engine=scheduling_engine,
    )
    finance_performance_query = ProjectFinancePerformanceQuery(
        performance_reader=finance_performance_reader,
        overview_reader=SqlAlchemyFinanceSnapshotReader(session=session),
        earned_value_authority=reporting_service,
        baseline_variance_authority=baseline_service,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    dashboard_service = DashboardService(
        reporting_service=reporting_service,
        task_service=task_service,
        project_service=project_service,
        resource_service=resource_service,
        register_service=register_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=platform_services.global_calendar_shim,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    data_import_service = DataImportService(
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    project_calendar_adapter = _pre_project_calendar_adapter  # reuse the instance wired into SchedulingEngine
    resource_capacity_calculator = ResourceCapacityCalculator(
        availability_service=enterprise_resource_availability,
    )
    resource_workload_service = ResourceWorkloadService(
        resource_repo=repositories.resource_repo,
        demand_reader=SqlAlchemyResourceWorkloadDemandReader(session=session),
        availability_service=enterprise_resource_availability,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
    )
    portfolio_resource_pool_service = PortfolioResourcePoolService(
        reader=SqlAlchemyPortfolioResourcePoolReader(session=session),
        calendar=platform_services.global_calendar_shim,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    logger.debug("Project Management core services built")
    register_project_management_approval_handlers(
        approval_service=platform_services.approval_service,
        user_session=platform_services.user_session,
        session=session,
        tenant_context_service=platform_services.tenant_context_service,
        module_catalog_service=platform_services.module_catalog_service,
        work_calendar_engine=work_calendar_engine,
        platform_calendar_resolver=platform_services.platform_calendar_resolver,
        calendar_assignment_service=platform_services.calendar_assignment_service,
        financial_period_service=platform_services.financial_period_service,
    )
    logger.debug("Project Management approval handlers registered")
    logger.debug(
        "Project Management service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return ProjectManagementServiceBundle(
        time_service=time_service,
        collaboration_service=collaboration_service,
        project_service=project_service,
        task_service=task_service,
        timesheet_service=timesheet_service,
        resource_service=resource_service,
        finance_governance_commands=finance_governance_commands,
        financial_configuration_service=financial_configuration_service,
        forecast_generation_service=forecast_generation_service,
        forecast_version_service=forecast_version_service,
        financial_change_service=financial_change_service,
        billing_profile_service=billing_profile_service,
        billing_preparation_service=billing_preparation_service,
        rate_card_service=rate_card_service,
        rate_card_resolver=rate_card_resolver,
        budget_service=budget_service,
        cost_entry_service=cost_entry_service,
        finance_worker_uow_factory=finance_governance_uow_factory,
        approved_time_consumer_factory=build_approved_time_consumer,
        procurement_consumer_factory=build_procurement_consumer,
        commitment_service=commitment_service,
        planned_cost_service=planned_cost_service,
        finance_workspace_query=finance_workspace_query,
        finance_performance_query=finance_performance_query,
        finance_service=finance_service,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        reporting_service=reporting_service,
        baseline_service=baseline_service,
        dashboard_service=dashboard_service,
        portfolio_service=portfolio_service,
        register_service=register_service,
        project_resource_service=project_resource_service,
        data_import_service=data_import_service,
        assignment_skill_validator=assignment_skill_validator,
        project_calendar_adapter=project_calendar_adapter,
        enterprise_resource_availability=enterprise_resource_availability,
        resource_capacity_calculator=resource_capacity_calculator,
        resource_workload_service=resource_workload_service,
        portfolio_resource_pool_service=portfolio_resource_pool_service,
    )

__all__ = ["ProjectManagementServiceBundle", "build_project_management_service_bundle"]
