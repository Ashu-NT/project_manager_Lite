from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from src.core.modules.project_management.infrastructure.composition.bootstrap import (
    APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
    PROCUREMENT_FINANCE_PRINCIPAL_NAME,
    build_project_management_repository_context,
    build_project_management_service_bundle,
    pm_notification_recipient_policy,
)
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.infrastructure.composition.bootstrap import (
    build_platform_repositories,
    build_platform_service_bundle,
)
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.resolver import IntegrationResolver
from src.infra.composition.global_overview_registry import (
    build_global_overview_service_bundle,
)
from src.infra.composition.integration.accounting.accounting_integration import (
    build_accounting_configuration_commands,
)
from src.infra.composition.service_graph import ServiceGraph
from src.infra.integration.approved_time_dispatcher import (
    ApprovedTimeFinancialDispatcher,
)
from src.infra.integration.procurement_financial_dispatcher import (
    ProcurementFinancialDispatcher,
)
from src.infra.time.system_clock import SystemClock

logger = logging.getLogger(__name__)


def build_service_graph(session: Session, *, accounting_adapter_ids: frozenset[str] = frozenset()) -> ServiceGraph:
    started = perf_counter()
    logger.debug("Service graph build begin session_type=%s", type(session).__name__)
    platform_repositories = build_platform_repositories(session)
    repositories = build_project_management_repository_context(session, platform_repositories)
    logger.debug(
        "Repository bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    platform_services = build_platform_service_bundle(
        session, platform_repositories,
        project_assignment_repo=repositories.pm.project_calendar_assignment_repo,
        resource_assignment_repo=repositories.pm.resource_calendar_assignment_repo,
        notification_recipient_policy=pm_notification_recipient_policy,
    )
    logger.debug(
        "Platform service bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    _delivery_clock = SystemClock()
    _time_financial_outbox_service = IntegrationOutboxService(
        repository=platform_repositories.time_financial_outbox_repo,
        owner_module="platform_time",
        clock=_delivery_clock,
    )
    _procurement_financial_outbox_service = IntegrationOutboxService(
        repository=platform_repositories.procurement_financial_outbox_repo,
        owner_module="inventory_procurement",
        clock=_delivery_clock,
    )
    project_management_services = build_project_management_service_bundle(
        session,
        repositories,
        platform_services,
        approved_time_outbox_service=_time_financial_outbox_service,
        accounting_adapter_ids=accounting_adapter_ids,
    )
    logger.debug(
        "Project Management service bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    global_overview_services = build_global_overview_service_bundle(
        session, platform_services, project_management_services
    )
    _module_registry = ModuleRegistry(platform_services.module_catalog_service)
    _integration_resolver = IntegrationResolver(_module_registry)
    _approved_time_financial_dispatcher = ApprovedTimeFinancialDispatcher(
        session=session,
        outbox_service=_time_financial_outbox_service,
        uow_factory=project_management_services.finance_worker_uow_factory,
        consumer_factory=project_management_services.approved_time_consumer_factory,
        principal_resolver=lambda: platform_services.service_principal_service.resolve_execution_principal(
            name=APPROVED_TIME_FINANCE_PRINCIPAL_NAME
        ),
    )
    _procurement_financial_dispatcher = ProcurementFinancialDispatcher(
        session=session,
        outbox_service=_procurement_financial_outbox_service,
        uow_factory=project_management_services.finance_worker_uow_factory,
        consumer_factory=project_management_services.procurement_consumer_factory,
        principal_resolver=lambda: platform_services.service_principal_service.resolve_execution_principal(
            name=PROCUREMENT_FINANCE_PRINCIPAL_NAME
        ),
    )
    project_management_services.time_service.set_approved_time_dispatcher(
        _approved_time_financial_dispatcher.dispatch_pending
    )
    try:
        _approved_time_financial_dispatcher.dispatch_pending(limit=50)
    except Exception:
        session.rollback()
        logger.exception("Approved Time startup replay failed; durable events remain pending")
    try:
        _procurement_financial_dispatcher.dispatch_pending(limit=50)
    except Exception:
        session.rollback()
        logger.exception("Procurement startup replay failed; durable events remain pending")
    graph = ServiceGraph(
        session=session,
        user_session=platform_services.user_session,
        platform_runtime_application_service=platform_services.platform_runtime_application_service,
        module_catalog_service=platform_services.module_catalog_service,
        module_registry=_module_registry,
        integration_resolver=_integration_resolver,
        time_financial_outbox_service=_time_financial_outbox_service,
        procurement_financial_outbox_service=_procurement_financial_outbox_service,
        approved_time_financial_dispatcher=_approved_time_financial_dispatcher,
        procurement_financial_dispatcher=_procurement_financial_dispatcher,
        time_service=project_management_services.time_service,
        auth_service=platform_services.auth_service,
        role_governance_service=platform_services.role_governance_service,
        tenant_role_administration_service=(
            platform_services.tenant_role_administration_service
        ),
        organization_service=platform_services.organization_service,
        tenant_context_service=platform_services.tenant_context_service,
        platform_view_invalidation_channel=platform_services.platform_view_invalidation_channel,
        tenant_admin_service=platform_services.tenant_admin_service,
        tenant_membership_service=platform_services.tenant_membership_service,
        service_principal_service=platform_services.service_principal_service,
        document_service=platform_services.document_service,
        party_service=platform_services.party_service,
        department_service=platform_services.department_service,
        site_service=platform_services.site_service,
        employee_service=platform_services.employee_service,
        master_data_exchange_service=platform_services.master_data_exchange_service,
        runtime_execution_service=platform_services.runtime_execution_service,
        access_service=platform_services.access_service,
        activity_service=platform_services.activity_service,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        financial_period_service=platform_services.financial_period_service,
        accounting_connector_commands=build_accounting_configuration_commands(
            session=session, platform_services=platform_services, installed_adapters=accounting_adapter_ids,
        ),
        notification_service=platform_services.notification_service,
        approval_service=platform_services.approval_service,
        collaboration_service=project_management_services.collaboration_service,
        project_service=project_management_services.project_service,
        task_service=project_management_services.task_service,
        timesheet_service=project_management_services.timesheet_service,
        resource_service=project_management_services.resource_service,
        finance_governance_commands=(
            project_management_services.finance_governance_commands
        ),
        financial_configuration_service=(
            project_management_services.financial_configuration_service
        ),
        forecast_generation_service=project_management_services.forecast_generation_service,
        forecast_version_service=project_management_services.forecast_version_service,
        financial_change_service=project_management_services.financial_change_service,
        billing_profile_service=project_management_services.billing_profile_service,
        billing_preparation_service=project_management_services.billing_preparation_service,
        rate_card_service=project_management_services.rate_card_service,
        rate_card_resolver=project_management_services.rate_card_resolver,
        budget_service=project_management_services.budget_service,
        cost_entry_service=project_management_services.cost_entry_service,
        commitment_service=project_management_services.commitment_service,
        planned_cost_service=project_management_services.planned_cost_service,
        finance_workspace_query=project_management_services.finance_workspace_query,
        finance_performance_query=project_management_services.finance_performance_query,
        finance_service=project_management_services.finance_service,
        work_calendar_engine=project_management_services.work_calendar_engine,
        scheduling_engine=project_management_services.scheduling_engine,
        reporting_service=project_management_services.reporting_service,
        baseline_service=project_management_services.baseline_service,
        dashboard_service=project_management_services.dashboard_service,
        portfolio_service=project_management_services.portfolio_service,
        register_service=project_management_services.register_service,
        project_resource_service=project_management_services.project_resource_service,
        data_import_service=project_management_services.data_import_service,
        assignment_skill_validator=project_management_services.assignment_skill_validator,
        platform_calendar_service=platform_services.platform_calendar_service,
        working_rule_service=platform_services.working_rule_service,
        calendar_exception_service=platform_services.calendar_exception_service,
        recurring_event_service=platform_services.recurring_event_service,
        shift_pattern_service=platform_services.shift_pattern_service,
        calendar_assignment_service=platform_services.calendar_assignment_service,
        platform_calendar_resolver=platform_services.platform_calendar_resolver,
        working_time_calculator=platform_services.working_time_calculator,
        resource_capacity_calculator=project_management_services.resource_capacity_calculator,
        resource_workload_service=project_management_services.resource_workload_service,
        enterprise_resource_availability=project_management_services.enterprise_resource_availability,
        portfolio_resource_pool_service=project_management_services.portfolio_resource_pool_service,
        action_center_service=global_overview_services.action_center_service,
        global_overview_service=global_overview_services.global_overview_service,
        global_overview_desktop_api=global_overview_services.global_overview_desktop_api,
        platform_notification_desktop_api=global_overview_services.platform_notification_desktop_api,
    )
    logger.debug(
        "Service graph build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return graph


def build_service_dict(session: Session, *, accounting_adapter_ids: frozenset[str] = frozenset()) -> dict[str, Any]:
    started = perf_counter()
    graph = build_service_graph(session, accounting_adapter_ids=accounting_adapter_ids)
    services = graph.as_dict()
    logger.debug(
        "Service dictionary build complete service_count=%s duration_ms=%.1f",
        len(services),
        (perf_counter() - started) * 1000,
    )
    return services
