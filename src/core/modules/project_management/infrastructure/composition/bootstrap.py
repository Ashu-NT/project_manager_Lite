"""Construct the Project Management service graph from supplied Platform capabilities."""

from __future__ import annotations

import logging
from time import perf_counter

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
    APPROVED_TIME_FINANCE_PRINCIPAL_NAME as APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
)
from src.core.modules.project_management.application.financials.integration.procurement_consumer import (
    PROCUREMENT_FINANCE_PRINCIPAL_NAME as PROCUREMENT_FINANCE_PRINCIPAL_NAME,
)
from src.core.modules.project_management.infrastructure.composition.bundle import (
    ProjectManagementServiceBundle,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.collaboration.services import (
    build_collaboration_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.dashboard.services import (
    build_dashboard_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.billing import (
    build_billing_services,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.budgets import (
    build_budget_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.changes import (
    build_financial_change_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.configuration import (
    build_financial_configuration_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.costs import (
    build_cost_services,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.forecasts import (
    build_forecast_services,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.governance_boundary import (
    build_finance_governance_boundary,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.governance_operations import (
    build_finance_governance_operations_factory,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.governed_ports import (
    wrap_finance_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.rates import (
    build_rate_card_services,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.reads import (
    build_finance_performance_query,
    build_finance_performance_services,
    build_finance_workspace_query,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.workers import (
    build_finance_worker_consumers,
    build_finance_worker_uow_factory,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.importers.services import (
    build_data_import_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.portfolio.services import (
    build_portfolio_resource_pool_service,
    build_portfolio_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.projects.services import (
    build_project_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.register.services import (
    build_register_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.reporting.services import (
    build_reporting_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.repositories import (
    build_project_management_repositories,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.resources.services import (
    build_project_resource_service,
    build_resource_planning_foundation,
    build_resource_planning_services,
    build_resource_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.scheduling.services import (
    build_baseline_service,
    build_scheduling_foundation,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.tasks.services import (
    build_task_service,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.timesheets.services import (
    build_timesheet_service,
)
from src.core.modules.project_management.infrastructure.composition.events.collaboration.registration import (
    register_collaboration_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.finance.billing import (
    register_billing_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.finance.budgets import (
    register_budget_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.finance.changes import (
    register_financial_change_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.finance.configuration import (
    register_financial_profile_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.finance.costs import (
    register_commitment_view_invalidation,
    register_cost_entry_view_invalidation,
    register_planned_cost_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.finance.forecasts import (
    register_forecast_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.finance.rates import (
    register_rate_card_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.portfolio.registration import (
    register_portfolio_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.projects.registration import (
    register_project_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.register.registration import (
    register_register_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.resources.registration import (
    register_resource_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.scheduling.registration import (
    register_baseline_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.events.tasks.registration import (
    register_task_events,
)
from src.core.modules.project_management.infrastructure.composition.events.timesheets.registration import (
    register_timesheet_view_invalidation,
)
from src.core.modules.project_management.infrastructure.composition.registrations.access import (
    register_project_scope_access,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.handlers import (
    register_project_management_approval_handlers,
)
from src.core.modules.project_management.infrastructure.composition.registrations.notifications import (
    pm_notification_recipient_policy,
)
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.time_management.time import TimeService
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
)
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkFactoryBase

logger = logging.getLogger(__name__)


def build_project_management_repository_context(
    session: Session, platform: PlatformRepositories
) -> ProjectManagementRepositoryContext:
    return ProjectManagementRepositoryContext(
        pm=build_project_management_repositories(session),
        platform=platform,
    )



def build_project_management_service_bundle(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    approved_time_outbox_service: IntegrationOutboxService | None = None,
    accounting_adapter_ids: frozenset[str] = frozenset(),
) -> ProjectManagementServiceBundle:
    started = perf_counter()
    logger.debug("Project Management service bundle build begin")
    for field_name in repositories.pm.__dataclass_fields__:
        repo = getattr(repositories.pm, field_name)
        if hasattr(repo, "_tenant_context_service"):
            repo._tenant_context_service = platform_services.tenant_context_service
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
    project_resource_service = build_project_resource_service(
        session,
        repositories,
        platform_services,
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
    assignment_skill_validator, enterprise_resource_availability = build_resource_planning_foundation(
        repositories,
        platform_services,
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
    financial_configuration_service = build_financial_configuration_service(
        session,
        repositories,
        platform_services,
    )
    rate_card_service, rate_card_resolver = build_rate_card_services(
        session,
        repositories,
        platform_services,
        clock=system_clock,
    )
    budget_service = build_budget_service(
        session,
        repositories,
        platform_services,
        clock=system_clock,
    )
    cost_entry_service, commitment_service, planned_cost_service = build_cost_services(
        session,
        repositories,
        platform_services,
        clock=system_clock,
        rate_resolver=rate_card_resolver,
    )
    finance_workspace_query = build_finance_workspace_query(
        session,
        platform_services,
        accounting_adapter_ids=accounting_adapter_ids,
    )
    reporting_service = build_reporting_service(
        session,
        repositories,
        platform_services,
        scheduling_engine=scheduling_engine,
        rate_resolver=rate_card_resolver,
    )
    finance_performance_reader, finance_service = build_finance_performance_services(
        session,
        platform_services,
        rate_resolver=rate_card_resolver,
    )
    forecast_version_service, forecast_generation_service = build_forecast_services(
        session,
        repositories,
        platform_services,
        clock=system_clock,
    )

    finance_governance_uow_factory = build_finance_worker_uow_factory(platform_services)
    build_approved_time_consumer, build_procurement_consumer = build_finance_worker_consumers(
        platform_services,
        clock=system_clock,
    )
    register_forecast_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_financial_change_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_planned_cost_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_commitment_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_cost_entry_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_budget_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_billing_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_financial_profile_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_rate_card_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    financial_change_service = build_financial_change_service(
        session,
        repositories,
        platform_services,
        task_service=task_service,
        clock=system_clock,
    )

    build_finance_governance_operations = build_finance_governance_operations_factory(
        platform_services,
        clock=system_clock,
        work_calendar_engine=work_calendar_engine,
        accounting_adapter_ids=accounting_adapter_ids,
    )
    finance_governance_commands = build_finance_governance_boundary(
        session,
        finance_governance_uow_factory,
        build_finance_governance_operations,
    )
    financial_configuration_service = wrap_finance_service(
        financial_configuration_service, finance_governance_commands, family="financial_setup"
    )
    budget_service = wrap_finance_service(
        budget_service, finance_governance_commands, family="budget"
    )
    forecast_version_service = wrap_finance_service(
        forecast_version_service, finance_governance_commands, family="forecast_version"
    )
    forecast_generation_service = wrap_finance_service(
        forecast_generation_service, finance_governance_commands, family="forecast_generation"
    )
    financial_change_service = wrap_finance_service(
        financial_change_service, finance_governance_commands, family="financial_change"
    )
    rate_card_service = wrap_finance_service(
        rate_card_service, finance_governance_commands, family="rate_card"
    )
    planned_cost_service = wrap_finance_service(
        planned_cost_service, finance_governance_commands, family="planned_cost"
    )
    cost_entry_service = wrap_finance_service(
        cost_entry_service, finance_governance_commands, family="cost_entry"
    )
    billing_profile_service, billing_preparation_service = build_billing_services(
        session,
        repositories,
        platform_services,
        clock=system_clock,
        rate_resolver=rate_card_resolver,
    )
    billing_profile_service = wrap_finance_service(
        billing_profile_service, finance_governance_commands, family="billing_profile"
    )
    billing_preparation_service = wrap_finance_service(
        billing_preparation_service, finance_governance_commands, family="billing_preparation"
    )
    register_collaboration_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    collaboration_service = build_collaboration_service(session, repositories, platform_services)
    register_portfolio_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    portfolio_service = build_portfolio_service(
        session,
        repositories,
        platform_services,
        project_calendar_adapter=_pre_project_calendar_adapter,
        rate_resolver=rate_card_resolver,
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
    finance_performance_query = build_finance_performance_query(
        session,
        platform_services,
        performance_reader=finance_performance_reader,
        reporting_service=reporting_service,
        baseline_service=baseline_service,
    )
    dashboard_service = build_dashboard_service(
        platform_services,
        reporting_service=reporting_service,
        task_service=task_service,
        project_service=project_service,
        resource_service=resource_service,
        register_service=register_service,
        scheduling_engine=scheduling_engine,
    )
    data_import_service = build_data_import_service(
        platform_services,
        project_service=project_service,
        task_service=task_service,
        resource_service=resource_service,
    )
    project_calendar_adapter = _pre_project_calendar_adapter  # reuse the instance wired into SchedulingEngine
    resource_capacity_calculator, resource_workload_service = build_resource_planning_services(
        session,
        repositories,
        platform_services,
        availability_service=enterprise_resource_availability,
    )
    portfolio_resource_pool_service = build_portfolio_resource_pool_service(
        session,
        platform_services,
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

__all__ = [
    "build_project_management_repository_context",
    "build_project_management_service_bundle",
    "pm_notification_recipient_policy",
]
