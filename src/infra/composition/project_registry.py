from __future__ import annotations

from src.core.platform.contract.port.time_management.calendar.calendar_protocol import CalendarProtocol

import logging
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.access import ScopedRolePolicy
from src.core.modules.project_management.infrastructure.persistence.uow.finance.billing_preparation_submission_unit_of_work import (
    SqlAlchemyBillingPreparationSubmissionUnitOfWorkFactory,
)
from src.core.modules.project_management.infrastructure.persistence.uow.finance.finance_governance_unit_of_work import (
    SqlAlchemyFinanceGovernanceUnitOfWorkFactory,
)
from src.core.modules.project_management.infrastructure.persistence.uow.resources.resource_unit_of_work import (
    SqlAlchemyResourceUnitOfWorkFactory,
)
from src.core.modules.project_management.application.resources.event_handlers.view_invalidation import (
    build_resource_capabilities_view_invalidation_handler,
    build_resource_list_view_invalidation_handler,
)
from src.core.modules.project_management.application.resources.resource_capability_events import (
    ResourceCapabilityChanged,
)
from src.core.modules.project_management.application.resources.resource_master_events import (
    ResourceMasterChanged,
)
from src.core.modules.project_management.application.financials.forecasts.event_handlers.view_invalidation import (
    build_forecast_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastDraftGenerated,
    ForecastLineChanged,
    ForecastVersionChanged,
)
from src.core.modules.project_management.application.financials.financial_changes.event_handlers.view_invalidation import (
    build_financial_change_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.financial_changes.financial_change_events import (
    FinancialChangeChanged,
)
from src.core.modules.project_management.application.financials.planned_costs.event_handlers.view_invalidation import (
    build_planned_cost_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.planned_costs.planned_cost_events import (
    PlannedCostSnapshotCalculated,
)
from src.core.modules.project_management.application.financials.commitments.event_handlers.view_invalidation import (
    build_commitment_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.commitments.commitment_events import (
    CommitmentLineChanged,
    CommitmentMatchChanged,
)
from src.core.modules.project_management.application.financials.event_handlers.view_invalidation import (
    build_financial_profile_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.configuration_events import (
    ProjectFinancialProfileTransitioned,
    ProjectFinancialProfileUpdated,
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
)
from src.core.modules.project_management.application.scheduling.baselines.event_handlers.view_invalidation import (
    build_baseline_view_invalidation_handler,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_events import (
    ProjectBaselineApproved,
    ProjectBaselineCreated,
    ProjectBaselineDeleted,
    ProjectBaselineRejected,
    ProjectBaselineSubmitted,
)
from src.core.modules.project_management.infrastructure.persistence.uow.scheduling.baseline_unit_of_work import (
    SqlAlchemyBaselineUnitOfWorkFactory,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.projects.project import (
    SqlAlchemyProjectRepository,
)
from src.core.modules.project_management.infrastructure.approval.baseline_apply_participant import (
    BaselineApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.billing_preparation_apply_participant import (
    BillingPreparationApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.budget_apply_participant import (
    BudgetApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.forecast_apply_participant import (
    ForecastApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.project_cost_apply_participant import (
    ProjectCostApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.task_apply_participant import (
    TaskApprovalParticipant,
)
from src.infra.composition.approval_apply_dependencies.baseline import build_baseline_approval_deps
from src.infra.composition.approval_apply_dependencies.billing_preparation import (
    build_billing_preparation_approval_deps,
)
from src.infra.composition.approval_apply_dependencies.budget import build_budget_approval_deps
from src.infra.composition.approval_apply_dependencies.forecast import (
    build_forecast_approval_deps,
)
from src.infra.composition.approval_apply_dependencies.financial_change import (
    build_financial_change_approval_deps,
)
from src.infra.composition.approval_apply_dependencies.project_cost import (
    build_project_cost_approval_deps,
)
from src.infra.composition.approval_apply_dependencies.task import build_task_approval_deps
from src.core.modules.project_management.access.policy import (
    PROJECT_SCOPE_ROLE_CHOICES,
    normalize_project_scope_role,
    resolve_project_scope_permissions,
)
from src.core.platform.application.time_management.time import TimeService
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import (
    ApprovedTimeLaborCostConsumer,
    BudgetService,
    FinancialConfigurationService,
    FinanceService,
    FinancialChangeService,
    ForecastGenerationService,
    ForecastVersionService,
    PlannedCostService,
    ProjectCostEntryService,
    ProjectCommitmentService,
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    ProcurementFinancialConsumer,
    ProjectFinanceWorkspaceQuery,
    ProjectFinancePerformanceQuery,
    ProjectRateCardService,
    RateCardResolver,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyEvmSeriesReader,
    SqlAlchemyFinanceBudgetReader,
    SqlAlchemyFinancePlannedCostReader,
    SqlAlchemyFinanceForecastReader,
    SqlAlchemyFinanceRateReader,
    SqlAlchemyFinanceChangeReader,
    SqlAlchemyFinanceBillingReader,
    SqlAlchemyFinancePerformanceReader,
    SqlAlchemyFinanceSetupReader,
    SqlAlchemyFinanceLookupReader,
    SqlAlchemyFinanceSnapshotReader,
)
from src.core.modules.project_management.application.financials.governance import (
    FinanceGovernanceCommandBoundary,
    FinanceGovernanceOperations,
    FinanceGovernedServicePort,
)
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
)
from src.core.modules.project_management.infrastructure.importers import DataImportService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.application.collaboration import CollaborationService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.application.scheduling.calendars.project_calendar_adapter import ProjectCalendarAdapter
from src.core.modules.project_management.application.resources.enterprise_resource_availability import EnterpriseResourceAvailabilityService
from src.core.modules.project_management.application.resources.resource_capacity_calculator import ResourceCapacityCalculator
from src.core.modules.project_management.application.resources.resource_workload_service import ResourceWorkloadService
from src.core.modules.project_management.application.resources.portfolio_resource_pool_service import PortfolioResourcePoolService
from src.core.modules.project_management.infrastructure.persistence.reads.portfolio import (
    SqlAlchemyPortfolioHeatmapReader,
    SqlAlchemyPortfolioResourcePoolReader,
    SqlAlchemyPortfolioScenarioReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.projects import (
    SqlAlchemyProjectCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceCatalogReader,
    SqlAlchemyResourceContextReader,
    SqlAlchemyResourceWorkloadDemandReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.register import (
    SqlAlchemyRegisterCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets import (
    SqlAlchemyTimesheetReviewReader,
    SqlAlchemyTimesheetWorkspaceReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.tasks import (
    SqlAlchemyTaskWorkspaceReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration import (
    SqlAlchemyCollaborationWorkspaceReader,
)
from src.infra.composition.platform_registry import PlatformServiceBundle
from src.infra.composition.repositories import RepositoryBundle


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
    approved_time_labor_cost_consumer: ApprovedTimeLaborCostConsumer
    procurement_financial_consumer: ProcurementFinancialConsumer
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
) -> ProjectManagementServiceBundle:
    started = perf_counter()
    logger.debug("Project Management service bundle build begin")
    logger.debug("Project Management platform registrations begin")
    platform_services.access_service.register_scope_policy(
        ScopedRolePolicy(
            scope_type="project",
            role_choices=PROJECT_SCOPE_ROLE_CHOICES,
            normalize_role=normalize_project_scope_role,
            resolve_permissions=resolve_project_scope_permissions,
        )
    )
    def _project_belongs_to_tenant(tenant_id: str, project_id: str) -> bool:
        # Legacy-signature resolver -- `AccessControlService`'s own pre-flight check and
        # `AuthService`'s effective-permissions read, both outside the RoleGovernance
        # transaction. Uses the tenant-scoped `get_for_tenant` (P5C-1 reopened-storeroom fix),
        # not the ambient-active-organization `get()`.
        return repositories.project_repo.get_for_tenant(project_id, tenant_id) is not None

    platform_services.access_service.register_scope_exists_resolver(
        "project",
        _project_belongs_to_tenant,
    )
    platform_services.auth_service.register_canonical_scope_tenant_resolver(
        "project",
        _project_belongs_to_tenant,
    )

    def _project_exists_for_role_governance(session: Session, tenant_id: str, project_id: str) -> bool:
        return SqlAlchemyProjectRepository(session).get_for_tenant(project_id, tenant_id) is not None

    def _project_organization_owner(session: Session, tenant_id: str, project_id: str) -> str | None:
        project = SqlAlchemyProjectRepository(session).get_for_tenant(project_id, tenant_id)
        return getattr(project, "organization_id", None)

    platform_services.role_governance_service.register_scope_exists_resolver(
        "project",
        _project_exists_for_role_governance,
    )
    platform_services.role_governance_service.register_organization_owner_resolver(
        "project",
        _project_organization_owner,
    )
    logger.debug("Project Management platform registrations complete")
    logger.debug("Project Management core services build begin")
    # GlobalCalendarShim is the enterprise-backed calendar. Used everywhere WorkCalendarEngine was.
    work_calendar_engine = platform_services.global_calendar_shim
    project_service = ProjectService(
        session,
        repositories.project_repo,
        repositories.task_repo,
        repositories.dependency_repo,
        repositories.assignment_repo,
        repositories.time_entry_repo,
        repositories.project_financial_profile_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        project_catalog_reader=SqlAlchemyProjectCatalogReader(session=session),
    )

    def _time_scope_organization_id(scope_type: str, scope_id: str) -> str | None:
        normalized_scope_type = str(scope_type or "").strip().lower()
        normalized_scope_id = str(scope_id or "").strip()
        if not normalized_scope_id:
            return None
        if normalized_scope_type == "project":
            project = repositories.project_repo.get(normalized_scope_id)
            return getattr(project, "organization_id", None) if project is not None else None
        if normalized_scope_type == "site":
            site = platform_services.site_repo.get(normalized_scope_id)
            return getattr(site, "organization_id", None) if site is not None else None
        return None

    timesheet_service = TimesheetService(
        session=session,
        assignment_repo=repositories.assignment_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
        employee_repo=repositories.employee_repo,
        time_entry_repo=repositories.time_entry_repo,
        timesheet_period_repo=repositories.timesheet_period_repo,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        scope_organization_resolver=_time_scope_organization_id,
        approved_time_outbox_service=approved_time_outbox_service,
        timesheet_workspace_reader=SqlAlchemyTimesheetWorkspaceReader(session=session),
        timesheet_review_reader=SqlAlchemyTimesheetReviewReader(session=session),
    )
    time_service: TimeService = timesheet_service
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
    )
    register_service = RegisterService(
        session=session,
        project_repo=repositories.project_repo,
        register_repo=repositories.register_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        register_catalog_reader=SqlAlchemyRegisterCatalogReader(session=session),
    )
    # Build enterprise calendar adapter here so it can be injected into SchedulingEngine.
    # Instantiated before scheduling_engine so we pass it in during construction.
    _pre_project_calendar_adapter = ProjectCalendarAdapter(
        resolver=platform_services.enterprise_calendar_resolver,
        assignment_service=platform_services.calendar_assignment_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        repositories.task_repo,
        repositories.dependency_repo,
        platform_services.global_calendar_shim,  # enterprise global as base calendar
        assignment_repo=repositories.assignment_repo,
        resource_repo=repositories.resource_repo,
        project_calendar_adapter=_pre_project_calendar_adapter,
    )
    logger.debug("Project Management scheduling foundation built")
    assignment_skill_validator = AssignmentSkillValidator(
        skill_repo=repositories.resource_skill_repo,
        cert_repo=repositories.resource_cert_repo,
        requirement_repo=repositories.task_skill_req_repo,
    )
    enterprise_resource_availability = EnterpriseResourceAvailabilityService(
        resolver=platform_services.enterprise_calendar_resolver,
        resource_repo=repositories.resource_repo,
    )
    task_service = TaskService(
        session,
        repositories.task_repo,
        repositories.dependency_repo,
        repositories.assignment_repo,
        repositories.time_entry_repo,
        repositories.timesheet_period_repo,
        timesheet_service,
        repositories.resource_repo,
        work_calendar_engine,
        scheduling_engine,
        repositories.project_resource_repo,
        repositories.project_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_catalog_service,
        notification_service=platform_services.notification_service,
        employee_repo=repositories.employee_repo,
        assignment_skill_validator=assignment_skill_validator,
        tenant_context_service=platform_services.tenant_context_service,
        task_workspace_reader=SqlAlchemyTaskWorkspaceReader(session=session),
        enterprise_resource_availability_service=enterprise_resource_availability,
    )
    # The resolver owns the effective-time source for immutable rate snapshots.
    system_clock = SystemClock()
    resource_read_reader = SqlAlchemyResourceCatalogReader(session=session)
    resource_context_reader = SqlAlchemyResourceContextReader(session=session)
    resource_uow_session_factory = sessionmaker(bind=platform_services.session.bind, future=True)
    resource_uow_factory = SqlAlchemyResourceUnitOfWorkFactory(
        session_factory=resource_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    platform_services.platform_post_commit_bus.subscribe(
        ResourceMasterChanged,
        build_resource_list_view_invalidation_handler(
            platform_services.platform_view_invalidation_channel
        ),
    )
    platform_services.platform_post_commit_bus.subscribe(
        ResourceCapabilityChanged,
        build_resource_capabilities_view_invalidation_handler(
            platform_services.platform_view_invalidation_channel
        ),
    )
    resource_service = ResourceService(
        session,
        repositories.resource_repo,
        repositories.assignment_repo,
        repositories.project_resource_repo,
        repositories.time_entry_repo,
        repositories.employee_repo,
        skill_repo=repositories.resource_skill_repo,
        cert_repo=repositories.resource_cert_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        resource_catalog_reader=resource_read_reader,
        resource_inspector_reader=resource_read_reader,
        resource_summary_reader=resource_read_reader,
        resource_projects_reader=resource_context_reader,
        resource_assignments_reader=resource_context_reader,
        resource_activity_reader=resource_context_reader,
        resource_capability_reader=resource_context_reader,
        department_service=platform_services.department_service,
        site_service=platform_services.site_service,
        uow_factory=resource_uow_factory,
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
    approved_time_labor_cost_consumer = ApprovedTimeLaborCostConsumer(cost_entry_service)
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
    procurement_financial_consumer = ProcurementFinancialConsumer(
        commitment_service=commitment_service,
        cost_entry_service=cost_entry_service,
        task_repo=repositories.task_repo,
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
    finance_workspace_query = ProjectFinanceWorkspaceQuery(
        setup_reader=SqlAlchemyFinanceSetupReader(session=session),
        lookup_reader=SqlAlchemyFinanceLookupReader(session=session),
        budget_reader=SqlAlchemyFinanceBudgetReader(session=session),
        planned_cost_reader=SqlAlchemyFinancePlannedCostReader(session=session),
        forecast_reader=SqlAlchemyFinanceForecastReader(session=session),
        rate_reader=SqlAlchemyFinanceRateReader(session=session),
        change_reader=SqlAlchemyFinanceChangeReader(session=session),
        billing_reader=SqlAlchemyFinanceBillingReader(session=session),
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    reporting_service = ReportingService(
        session=session,
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
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    finance_service = FinanceService(
        rate_resolver=rate_card_resolver,
        finance_snapshot_reader=SqlAlchemyFinanceSnapshotReader(session=session),
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
    _financial_profile_view_invalidation_handler = build_financial_profile_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _financial_profile_event_type in (
        ProjectFinancialProfileUpdated,
        ProjectFinancialProfileTransitioned,
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
        post_commit_actions = []
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
        change_operations._approval_requested_staged = lambda approval: (
            post_commit_actions.append(
                lambda: platform_services.approval_service.publish_requested(approval)
            )
        )
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
        commitment_operations = ProjectCommitmentService(
            session=uow._session,
            commitment_repo=uow.commitments,
            cost_entry_repo=uow.cost_entries,
            project_repo=uow.projects,
            financial_profile_repo=uow.profiles,
            cost_code_repo=uow.cost_codes,
            task_repo=uow.tasks,
            party_repo=repositories.party_repo,
            site_repo=repositories.site_repo,
            clock=system_clock,
            user_session=platform_services.user_session,
            enterprise_audit_service=uow._enterprise_audit_service,
            module_catalog_service=platform_services.module_catalog_service,
            tenant_context_service=platform_services.tenant_context_service,
            record_event=uow.record_event,
        )
        return FinanceGovernanceOperations(
            budgets=budget_operations,
            forecast_versions=forecast_version_operations,
            forecast_generation=forecast_generation_operations,
            financial_changes=change_operations,
            financial_setup=setup_operations,
            rate_cards=rate_card_operations,
            planned_costs=planned_cost_operations,
            commitments=commitment_operations,
            post_commit_actions=post_commit_actions,
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
    commitment_service = FinanceGovernedServicePort(
        read_service=commitment_service,
        boundary=finance_governance_commands,
        family="commitment",
        mutations=frozenset(
            {"ingest_procurement_source", "match_cost_entry", "reverse_match"}
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
    billing_preparation_submission_uow_session_factory = sessionmaker(
        bind=platform_services.session.bind, future=True
    )
    billing_preparation_submission_uow_factory = SqlAlchemyBillingPreparationSubmissionUnitOfWorkFactory(
        session_factory=billing_preparation_submission_uow_session_factory,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
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
        submission_uow_factory=billing_preparation_submission_uow_factory,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
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
        notification_service=platform_services.notification_service,
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
    )
    baseline_uow_factory = SqlAlchemyBaselineUnitOfWorkFactory(
        session=session,
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
    )
    _baseline_view_invalidation_handler = build_baseline_view_invalidation_handler(
        platform_services.platform_view_invalidation_channel
    )
    for _baseline_event_type in (
        ProjectBaselineCreated,
        ProjectBaselineSubmitted,
        ProjectBaselineApproved,
        ProjectBaselineRejected,
        ProjectBaselineDeleted,
    ):
        platform_services.platform_post_commit_bus.subscribe(
            _baseline_event_type, _baseline_view_invalidation_handler
        )
    baseline_service = BaselineService(
        session=session,
        project_repo=repositories.project_repo,
        task_repo=repositories.task_repo,
        planned_cost_repo=repositories.planned_cost_repo,
        baseline_repo=repositories.baseline_repo,
        scheduling=scheduling_engine,
        calendar=platform_services.global_calendar_shim,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        approval_service=platform_services.approval_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        uow_factory=baseline_uow_factory.create,
    )
    finance_performance_query = ProjectFinancePerformanceQuery(
        performance_reader=SqlAlchemyFinancePerformanceReader(session=session),
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
    _register_project_management_approval_handlers(
        approval_service=platform_services.approval_service,
        user_session=platform_services.user_session,
        session=session,
        tenant_context_service=platform_services.tenant_context_service,
        module_catalog_service=platform_services.module_catalog_service,
        work_calendar_engine=work_calendar_engine,
        enterprise_calendar_resolver=platform_services.enterprise_calendar_resolver,
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
        approved_time_labor_cost_consumer=approved_time_labor_cost_consumer,
        procurement_financial_consumer=procurement_financial_consumer,
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


def _register_project_management_approval_handlers(
    *,
    approval_service,
    user_session=None,
    session=None,
    tenant_context_service=None,
    module_catalog_service=None,
    work_calendar_engine=None,
    enterprise_calendar_resolver=None,
    calendar_assignment_service=None,
    financial_period_service=None,
) -> None:
    """P4 Step 2 (ADR-005 Section 24, Round 7/8): every request type below is now backed by a
    module-owned, session-parameterized approval transaction participant, whose bound
    apply/reject method is registered directly, alongside a `dependencies_factory(session)`
    closure over this call site's ambient collaborators. `ApprovalService` itself now calls
    `dependencies_factory(uow_session)` once per `approve_and_apply`/`reject` call, against its
    own fresh `PlatformUnitOfWork` Session -- never a Session fixed at composition time.
    See src/core/modules/project_management/infrastructure/approval/ and
    src/infra/composition/approval_apply_dependencies/ for each family's participant/deps-factory.
    """
    baseline_participant = BaselineApprovalParticipant()
    approval_service.register_apply_handler(
        "baseline.create",
        baseline_participant.apply,
        dependencies_factory=lambda uow_session: build_baseline_approval_deps(
            uow_session,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            module_catalog_service=module_catalog_service,
            calendar=work_calendar_engine,
        ),
    )

    task_participant = TaskApprovalParticipant()
    task_dependencies_factory = lambda uow_session: build_task_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        module_catalog_service=module_catalog_service,
        work_calendar_engine=work_calendar_engine,
        enterprise_calendar_resolver=enterprise_calendar_resolver,
        calendar_assignment_service=calendar_assignment_service,
    )
    approval_service.register_apply_handler(
        "dependency.add",
        task_participant.apply_dependency_add,
        dependencies_factory=task_dependencies_factory,
    )
    approval_service.register_apply_handler(
        "dependency.remove",
        task_participant.apply_dependency_remove,
        dependencies_factory=task_dependencies_factory,
    )
    approval_service.register_apply_handler(
        "dependency.update",
        task_participant.apply_dependency_update,
        dependencies_factory=task_dependencies_factory,
    )
    approval_service.register_apply_handler(
        "task.constraint.update",
        task_participant.apply_task_constraint_update,
        dependencies_factory=task_dependencies_factory,
    )
    approval_service.register_apply_handler(
        "scheduling.leveling.apply",
        task_participant.apply_resource_leveling_plan,
        dependencies_factory=task_dependencies_factory,
    )

    budget_participant = BudgetApprovalParticipant()
    budget_dependencies_factory = lambda uow_session: build_budget_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        module_catalog_service=module_catalog_service,
    )
    approval_service.register_apply_handler(
        "budget.approve",
        budget_participant.apply,
        dependencies_factory=budget_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "budget.approve",
        budget_participant.reject,
        dependencies_factory=budget_dependencies_factory,
    )

    forecast_participant = ForecastApprovalParticipant()
    forecast_dependencies_factory = lambda uow_session: build_forecast_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        module_catalog_service=module_catalog_service,
    )
    approval_service.register_apply_handler(
        "forecast.approve",
        forecast_participant.apply,
        dependencies_factory=forecast_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "forecast.approve",
        forecast_participant.reject,
        dependencies_factory=forecast_dependencies_factory,
    )

    project_cost_participant = ProjectCostApprovalParticipant()
    project_cost_dependencies_factory = lambda uow_session: build_project_cost_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        financial_period_service=financial_period_service,
        module_catalog_service=module_catalog_service,
    )
    approval_service.register_apply_handler(
        "project_cost.approve",
        project_cost_participant.apply,
        dependencies_factory=project_cost_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "project_cost.approve",
        project_cost_participant.reject,
        dependencies_factory=project_cost_dependencies_factory,
    )

    financial_change_participant = FinancialChangeApprovalParticipant()
    financial_change_dependencies_factory = lambda uow_session: build_financial_change_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        work_calendar_engine=work_calendar_engine,
        module_catalog_service=module_catalog_service,
    )
    approval_service.register_apply_handler(
        "financial_change.apply",
        financial_change_participant.apply,
        dependencies_factory=financial_change_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "financial_change.apply",
        financial_change_participant.reject,
        dependencies_factory=financial_change_dependencies_factory,
    )

    billing_preparation_participant = BillingPreparationApprovalParticipant()
    billing_preparation_dependencies_factory = (
        lambda uow_session: build_billing_preparation_approval_deps(
            uow_session,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            module_catalog_service=module_catalog_service,
        )
    )
    approval_service.register_apply_handler(
        "project_billing_preparation.approve",
        billing_preparation_participant.apply,
        dependencies_factory=billing_preparation_dependencies_factory,
    )
    approval_service.register_reject_handler(
        "project_billing_preparation.approve",
        billing_preparation_participant.reject,
        dependencies_factory=billing_preparation_dependencies_factory,
    )


__all__ = ["ProjectManagementServiceBundle", "build_project_management_service_bundle"]
