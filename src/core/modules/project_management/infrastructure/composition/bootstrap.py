"""Construct the Project Management service graph from supplied Platform capabilities."""

from __future__ import annotations

import logging
from time import perf_counter

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.infrastructure.composition.bundle import (
    ProjectManagementServiceBundle,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.collaboration.services import (
    build_collaboration_capabilities,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.dashboard.services import (
    build_dashboard_capabilities,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.billing import (
    build_billing_queries,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.budgets import (
    build_budget_query,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.changes import (
    build_financial_change_queries,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.configuration import (
    build_financial_configuration_query,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.costs import (
    build_cost_queries,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.forecasts import (
    build_forecast_version_query,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.governance_boundary import (
    build_finance_governance_boundary,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.governance_operations import (
    build_finance_governance_operations_factory,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.finance.rates import (
    build_rate_card_query,
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
    build_portfolio_capabilities,
    build_portfolio_resource_pool_query,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.projects.services import (
    build_project_capabilities,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.register.services import (
    build_register_capabilities,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.reporting.services import (
    build_reporting_capabilities,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.repositories import (
    build_project_management_repositories,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.resources.services import (
    build_project_resource_capabilities,
    build_resource_capabilities,
    build_resource_planning_foundation,
    build_resource_planning_services,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.scheduling.queries import (
    build_schedule_change_impact_query,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.scheduling.services import (
    build_baseline_capabilities,
    build_scheduling_foundation,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.tasks.services import (
    build_task_capabilities,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.timesheets.services import (
    build_timesheet_capabilities,
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
from src.core.modules.project_management.infrastructure.importers.tasks.capabilities import (
    TaskImportCapabilities,
)
from src.core.platform.application.integration import IntegrationOutboxService
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
    project_capabilities = build_project_capabilities(
        session,
        repositories,
        platform_services,
        shared_session_uow_factory,
    )

    timesheet_capabilities = build_timesheet_capabilities(
        session,
        repositories,
        platform_services,
        approved_time_outbox_service=approved_time_outbox_service,
    )
    register_timesheet_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    project_resource_capabilities = build_project_resource_capabilities(
        repositories,
        platform_services,
        shared_uow_factory=shared_session_uow_factory,
    )
    register_register_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    register_capabilities = build_register_capabilities(session, repositories, platform_services)
    register_query = register_capabilities.query
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
    task_capabilities = build_task_capabilities(
        session,
        repositories,
        platform_services,
        time_entry_queries=timesheet_capabilities.time_entry_queries,
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
    resource_capabilities = build_resource_capabilities(
        session,
        repositories,
        platform_services,
    )
    financial_configuration_query = build_financial_configuration_query(repositories, platform_services)
    rate_card_query, rate_card_resolver = build_rate_card_query(
        session,
        repositories,
        platform_services,
        clock=system_clock,
    )
    budget_query = build_budget_query(repositories, platform_services)
    cost_entry_query, commitment_query, planned_cost_query = build_cost_queries(repositories, platform_services)
    finance_workspace_query = build_finance_workspace_query(
        session,
        platform_services,
        accounting_adapter_ids=accounting_adapter_ids,
    )
    reporting = build_reporting_capabilities(
        session,
        repositories,
        platform_services,
        scheduling_engine=scheduling_engine,
        rate_resolver=rate_card_resolver,
    )
    finance_performance_reader, finance_snapshot_query = build_finance_performance_services(
        session,
        platform_services,
        rate_resolver=rate_card_resolver,
    )
    forecast_version_query = build_forecast_version_query(repositories, platform_services)

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
    financial_change_query = build_financial_change_queries(repositories, platform_services)

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
    billing_profile_query, billing_preparation_query = build_billing_queries(repositories, platform_services)
    register_collaboration_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    collaboration = build_collaboration_capabilities(session, repositories, platform_services)
    register_portfolio_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    portfolio_resource_pool_query = build_portfolio_resource_pool_query(
        session,
        platform_services,
    )
    portfolio = build_portfolio_capabilities(
        session,
        repositories,
        platform_services,
        project_calendar_adapter=_pre_project_calendar_adapter,
        resource_pool_query=portfolio_resource_pool_query,
    )
    register_baseline_view_invalidation(
        platform_services.platform_post_commit_bus,
        platform_services.platform_view_invalidation_channel,
    )
    baseline_capabilities = build_baseline_capabilities(
        session,
        repositories,
        platform_services,
        scheduling_engine=scheduling_engine,
    )
    baseline_query = baseline_capabilities.query
    schedule_change_impact_query = build_schedule_change_impact_query(
        task_repo=repositories.pm.task_repo,
        dependency_repo=repositories.pm.dependency_repo,
        calendar=work_calendar_engine,
        baseline_lookup=baseline_query,
    )
    finance_performance_query = build_finance_performance_query(
        session,
        platform_services,
        performance_reader=finance_performance_reader,
        earned_value_report=reporting.earned_value,
        baseline_query=baseline_query,
    )
    dashboard = build_dashboard_capabilities(
        platform_services,
        reporting=reporting,
        task_lookup=task_capabilities.lookup,
        project_query=project_capabilities.query,
        resource_query=resource_capabilities.query,
        register_query=register_query,
        scheduling_engine=scheduling_engine,
    )
    data_import_service = build_data_import_service(
        platform_services,
        project_query=project_capabilities.query,
        project_create=project_capabilities.create,
        project_update=project_capabilities.update,
        project_status=project_capabilities.status,
        task_capabilities=TaskImportCapabilities(
            lookup=task_capabilities.lookup,
            lifecycle=task_capabilities.lifecycle,
            hierarchy=task_capabilities.hierarchy,
            progress=task_capabilities.progress,
        ),
        resource_query=resource_capabilities.query,
        resource_master_commands=resource_capabilities.master_commands,
    )
    project_calendar_adapter = _pre_project_calendar_adapter  # reuse the instance wired into SchedulingEngine
    resource_capacity_calculator, resource_workload_query = build_resource_planning_services(
        session,
        repositories,
        platform_services,
        availability_service=enterprise_resource_availability,
    )
    logger.debug("Project Management core services built")
    register_project_management_approval_handlers(
        approval_participants=platform_services.approval_participants,
        user_session=platform_services.user_session,
        session=session,
        tenant_context_service=platform_services.tenant_context_service,
        module_catalog_service=platform_services.module_catalog_service,
        work_calendar_engine=work_calendar_engine,
        platform_calendar_resolver=platform_services.platform_calendar_resolver,
        financial_period_queries=platform_services.financial_period_queries,
    )
    logger.debug("Project Management approval handlers registered")
    logger.debug(
        "Project Management service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return ProjectManagementServiceBundle(
        time_entry_commands=timesheet_capabilities.time_entries,
        time_entry_queries=timesheet_capabilities.time_entry_queries,
        timesheet_period_transitions=timesheet_capabilities.period_transitions,
        collaboration_comment_commands=collaboration.comment_commands,
        collaboration_comment_engagement=collaboration.comment_engagement,
        collaboration_presence_commands=collaboration.presence_commands,
        collaboration_comment_query=collaboration.comment_query,
        collaboration_document_query=collaboration.document_query,
        collaboration_inbox_query=collaboration.inbox_query,
        collaboration_presence_query=collaboration.presence_query,
        project_query=project_capabilities.query,
        project_create=project_capabilities.create,
        project_update=project_capabilities.update,
        project_status=project_capabilities.status,
        project_deletion=project_capabilities.deletion,
        task_hierarchy_query=task_capabilities.hierarchy_query,
        task_deletion_commands=task_capabilities.deletion,
        task_progress_commands=task_capabilities.progress,
        task_schedule_changes=task_capabilities.schedule_changes,
        task_hierarchy_commands=task_capabilities.hierarchy,
        task_constraint_commands=task_capabilities.constraints,
        task_leveling_commands=task_capabilities.leveling,
        task_lifecycle_commands=task_capabilities.lifecycle,
        task_dependency_commands=task_capabilities.dependencies,
        task_dependency_query=task_capabilities.dependency_query,
        task_uow_scope=task_capabilities.uow_scope,
        task_workspace_query=task_capabilities.workspace,
        task_detail_query=task_capabilities.detail,
        task_dependency_diagnostics=task_capabilities.dependency_diagnostics,
        task_lookup_query=task_capabilities.lookup,
        task_assignment_commands=task_capabilities.assignment,
        task_time_entries=task_capabilities.time_entries,
        timesheet_workspace_query=timesheet_capabilities.workspace_queries,
        timesheet_workspace_commands=timesheet_capabilities.workspace_commands,
        timesheet_review_query=timesheet_capabilities.review_queries,
        timesheet_period_query=timesheet_capabilities.period_queries,
        resource_query=resource_capabilities.query,
        resource_master_commands=resource_capabilities.master_commands,
        resource_capability_commands=resource_capabilities.capability_commands,
        resource_capability_query=resource_capabilities.capability_query,
        resource_context_query=resource_capabilities.context_query,
        finance_governance_commands=finance_governance_commands,
        financial_configuration_query=financial_configuration_query,
        forecast_version_query=forecast_version_query,
        financial_change_query=financial_change_query,
        billing_profile_query=billing_profile_query,
        billing_preparation_query=billing_preparation_query,
        rate_card_query=rate_card_query,
        rate_card_resolver=rate_card_resolver,
        budget_query=budget_query,
        cost_entry_query=cost_entry_query,
        finance_worker_uow_factory=finance_governance_uow_factory,
        approved_time_consumer_factory=build_approved_time_consumer,
        procurement_consumer_factory=build_procurement_consumer,
        commitment_query=commitment_query,
        planned_cost_query=planned_cost_query,
        finance_workspace_query=finance_workspace_query,
        finance_performance_query=finance_performance_query,
        finance_snapshot_query=finance_snapshot_query,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        project_kpi_report=reporting.kpi,
        earned_value_report=reporting.earned_value,
        cost_breakdown_report=reporting.cost_breakdown,
        baseline_compare_report=reporting.baseline_compare,
        schedule_variance_report=reporting.schedule_variance,
        profitability_report=reporting.profitability,
        labor_report=reporting.labor,
        baseline_query=baseline_query,
        project_dashboard_query=dashboard.project,
        baseline_commands=baseline_capabilities.commands,
        schedule_change_impact_query=schedule_change_impact_query,
        portfolio_dashboard_query=dashboard.portfolio,
        portfolio_intake_query=portfolio.intake_query,
        portfolio_intake_commands=portfolio.intake_commands,
        portfolio_template_query=portfolio.template_query,
        portfolio_template_commands=portfolio.template_commands,
        portfolio_scenario_query=portfolio.scenario_query,
        portfolio_scenario_commands=portfolio.scenario_commands,
        portfolio_dependency_query=portfolio.dependency_query,
        portfolio_dependency_commands=portfolio.dependency_commands,
        portfolio_executive_query=portfolio.executive_query,
        register_query=register_query,
        register_lifecycle_commands=register_capabilities.lifecycle,
        project_resource_query=project_resource_capabilities.query,
        project_resource_commands=project_resource_capabilities.commands,
        data_import_service=data_import_service,
        assignment_skill_validator=assignment_skill_validator,
        project_calendar_adapter=project_calendar_adapter,
        enterprise_resource_availability=enterprise_resource_availability,
        resource_capacity_calculator=resource_capacity_calculator,
        resource_workload_query=resource_workload_query,
        portfolio_resource_pool_query=portfolio_resource_pool_query,
    )

__all__ = [
    "build_project_management_repository_context",
    "build_project_management_service_bundle",
    "pm_notification_recipient_policy",
]
