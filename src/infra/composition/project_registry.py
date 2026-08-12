from __future__ import annotations

from src.core.platform.contract.time_management.calendar.calendar_protocol import CalendarProtocol

import logging
from dataclasses import dataclass
from datetime import date
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.access import ScopedRolePolicy
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.contract.approval.contracts import (
    ApprovalHandlerResult,
    ApprovalPostCommitEvent,
)
from src.core.modules.project_management.domain.enums import DependencyType
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
    ProjectRateCardService,
    RateCardResolver,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.finance.rate_cards.rate_resolution_reader import (
    SqlAlchemyRateResolutionReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.financials import (
    SqlAlchemyEvmSeriesReader,
    SqlAlchemyFinanceSnapshotReader,
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
)
from src.core.modules.project_management.infrastructure.persistence.reads.register import (
    SqlAlchemyRegisterCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets import (
    SqlAlchemyTimesheetReviewReader,
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


def _as_dependency_type(value: Any) -> DependencyType:
    if isinstance(value, DependencyType):
        return value
    return DependencyType((value or DependencyType.FINISH_TO_START.value))


@dataclass(frozen=True)
class ProjectManagementServiceBundle:
    time_service: TimeService
    collaboration_service: CollaborationService
    project_service: ProjectService
    task_service: TaskService
    timesheet_service: TimesheetService
    resource_service: ResourceService
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
        return (
            platform_services.tenant_context_service.require_active_tenant_id(
                operation_label="validate project access scope"
            )
            == tenant_id
            and repositories.project_repo.get(project_id) is not None
        )

    platform_services.access_service.register_scope_exists_resolver(
        "project",
        _project_belongs_to_tenant,
    )
    platform_services.role_governance_service.register_scope_exists_resolver(
        "project",
        _project_belongs_to_tenant,
    )
    platform_services.auth_service.register_canonical_scope_tenant_resolver(
        "project",
        _project_belongs_to_tenant,
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
    )
    # Shared by ResourceService (legacy rate-line seeding/supersession) and
    # RateCardResolver (RateSelectionSnapshot.resolved_at) — one time source,
    # not two independent ways of asking "what time is it."
    system_clock = SystemClock()
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
        project_rate_card_repo=repositories.project_rate_card_repo,
        clock=system_clock,
        resource_catalog_reader=SqlAlchemyResourceCatalogReader(session=session),
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
        profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        budget_repo=repositories.project_budget_repo,
        rate_card_repo=repositories.project_rate_card_repo,
        planned_cost_repo=repositories.planned_cost_repo,
        task_repo=repositories.task_repo,
        resource_repo=repositories.resource_repo,
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
    collaboration_service = CollaborationService(
        session=session,
        comment_repo=repositories.task_comment_repo,
        presence_repo=repositories.task_presence_repo,
        task_repo=repositories.task_repo,
        project_repo=repositories.project_repo,
        user_repo=repositories.user_repo,
        audit_repo=repositories.audit_entry_repo,
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
    enterprise_resource_availability = EnterpriseResourceAvailabilityService(
        resolver=platform_services.enterprise_calendar_resolver,
        resource_repo=repositories.resource_repo,
    )
    resource_capacity_calculator = ResourceCapacityCalculator(
        availability_service=enterprise_resource_availability,
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
        baseline_service=baseline_service,
        task_service=task_service,
        budget_service=budget_service,
        cost_entry_service=cost_entry_service,
        financial_change_service=financial_change_service,
        billing_preparation_service=billing_preparation_service,
        user_session=platform_services.user_session,
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
        portfolio_resource_pool_service=portfolio_resource_pool_service,
    )


def _register_project_management_approval_handlers(
    *,
    approval_service,
    baseline_service: BaselineService,
    task_service: TaskService,
    budget_service: BudgetService,
    cost_entry_service: ProjectCostEntryService,
    financial_change_service: FinancialChangeService,
    billing_preparation_service: ProjectBillingPreparationService,
    user_session=None,
) -> None:
    def _result(signal_name: str, payload: str) -> ApprovalHandlerResult:
        return ApprovalHandlerResult(
            post_commit_events=(ApprovalPostCommitEvent(signal_name, payload),)
        )

    def _apply_baseline(req) -> ApprovalHandlerResult:
        project_id = req.payload["project_id"]

        baseline_service._apply_baseline_creation_decision(
            project_id=project_id,
            name=req.payload.get("name") or "Baseline",
            rate_as_of=date.today(),
            commit=False,
        )
        return _result("baseline_changed", project_id)

    def _apply_dependency_add(req) -> ApprovalHandlerResult:
        task_service._apply_dependency_add_decision(
            predecessor_id=req.payload["predecessor_id"],
            successor_id=req.payload["successor_id"],
            dependency_type=_as_dependency_type(req.payload.get("dependency_type", "FS")),
            lag_days=int(req.payload.get("lag_days", 0) or 0),
            commit=False,
        )
        return _result("tasks_changed", req.project_id or "")

    def _apply_dependency_remove(req) -> ApprovalHandlerResult:
        task_service._apply_dependency_remove_decision(
            dependency_id=req.payload["dependency_id"],
            commit=False,
        )
        return _result("tasks_changed", req.project_id or "")

    def _require_financial_decision_actor() -> str:
        principal = user_session.principal if user_session else None
        if principal is None:
            raise BusinessRuleError(
                "An authenticated principal is required to decide a financial approval.",
                code="PROJECT_FINANCIAL_APPROVAL_ACTOR_REQUIRED",
            )
        return principal.user_id

    def _apply_budget_approval(req) -> ApprovalHandlerResult:
        budget = budget_service._apply_approval_decision(
            budget_id=req.payload["budget_id"],
            approved_by=_require_financial_decision_actor(),
            expected_version=req.payload["expected_version"],
            notes=req.payload.get("notes", ""),
            commit=False,
        )
        return _result("budgets_changed", budget.project_id)

    def _apply_budget_rejection(req) -> ApprovalHandlerResult:
        budget = budget_service._apply_rejection_decision(
            budget_id=req.payload["budget_id"],
            rejected_by=_require_financial_decision_actor(),
            expected_version=req.payload["expected_version"],
            notes=req.payload.get("notes", ""),
            commit=False,
        )
        return _result("budgets_changed", budget.project_id)

    def _apply_cost_entry_approval(req) -> ApprovalHandlerResult:
        entry = cost_entry_service._apply_approval_decision(
            entry_id=req.payload["entry_id"],
            expected_version=req.payload["expected_version"],
            actor_id=_require_financial_decision_actor(),
            commit=False,
        )
        return _result("cost_entries_changed", entry.project_id)

    def _apply_cost_entry_rejection(req) -> ApprovalHandlerResult:
        entry = cost_entry_service._apply_rejection_decision(
            entry_id=req.payload["entry_id"],
            expected_version=req.payload["expected_version"],
            actor_id=_require_financial_decision_actor(),
            notes=req.payload.get("notes", ""),
            commit=False,
        )
        return _result("cost_entries_changed", entry.project_id)

    def _apply_financial_change(req) -> ApprovalHandlerResult:
        change = financial_change_service._apply_approval_decision(
            change_id=req.payload["change_id"],
            approval_request_id=req.id,
            applied_by=_require_financial_decision_actor(),
            commit=False,
        )
        events = [
            ApprovalPostCommitEvent("financial_changes_changed", change.project_id)
        ]
        if change.applied_budget_id:
            events.append(ApprovalPostCommitEvent("budgets_changed", change.project_id))
        if change.applied_forecast_id:
            events.append(ApprovalPostCommitEvent("forecasts_changed", change.project_id))
        if change.applied_schedule_count:
            events.append(ApprovalPostCommitEvent("tasks_changed", change.project_id))
        return ApprovalHandlerResult(post_commit_events=tuple(events))

    def _reject_financial_change(req) -> ApprovalHandlerResult:
        change = financial_change_service._apply_rejection_decision(
            change_id=req.payload["change_id"],
            approval_request_id=req.id,
            rejected_by=_require_financial_decision_actor(),
            notes=req.decision_note or "",
            commit=False,
        )
        return _result("financial_changes_changed", change.project_id)

    def _approve_billing_preparation(req) -> ApprovalHandlerResult:
        preparation = billing_preparation_service._apply_approval_decision(
            req.payload["preparation_id"],
            approved_by=_require_financial_decision_actor(),
            expected_version=req.payload["expected_version"] + 1,
            commit=False,
        )
        return _result("billing_preparations_changed", preparation.project_id)

    def _reject_billing_preparation(req) -> ApprovalHandlerResult:
        preparation = billing_preparation_service._apply_rejection_decision(
            req.payload["preparation_id"],
            rejected_by=_require_financial_decision_actor(),
            expected_version=req.payload["expected_version"] + 1,
            notes=req.decision_note or "",
            commit=False,
        )
        return _result("billing_preparations_changed", preparation.project_id)

    approval_service.register_apply_handler(
        "baseline.create",
        _apply_baseline,
    )
    approval_service.register_apply_handler(
        "dependency.add",
        _apply_dependency_add,
    )
    approval_service.register_apply_handler(
        "dependency.remove",
        _apply_dependency_remove,
    )
    approval_service.register_apply_handler(
        "budget.approve",
        _apply_budget_approval,
    )
    approval_service.register_reject_handler(
        "budget.approve",
        _apply_budget_rejection,
    )
    approval_service.register_apply_handler(
        "project_cost.approve",
        _apply_cost_entry_approval,
    )
    approval_service.register_reject_handler(
        "project_cost.approve",
        _apply_cost_entry_rejection,
    )
    approval_service.register_apply_handler(
        "financial_change.apply",
        _apply_financial_change,
    )
    approval_service.register_reject_handler(
        "financial_change.apply",
        _reject_financial_change,
    )
    approval_service.register_apply_handler(
        "project_billing_preparation.approve",
        _approve_billing_preparation,
    )
    approval_service.register_reject_handler(
        "project_billing_preparation.approve",
        _reject_billing_preparation,
    )


__all__ = ["ProjectManagementServiceBundle", "build_project_management_service_bundle"]
