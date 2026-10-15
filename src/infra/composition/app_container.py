from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.cost.entries.approved_time_consumer import (
    APPROVED_TIME_FINANCE_PRINCIPAL_NAME,
)
from src.core.modules.project_management.application.financials.integration.procurement_consumer import (
    PROCUREMENT_FINANCE_PRINCIPAL_NAME,
)
from src.core.modules.project_management.infrastructure.composition.bootstrap import (
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
from src.infra.composition.integration.bundle import IntegrationRuntimeBundle
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
        principal_resolver=lambda: platform_services.service_principal_query.resolve_execution_principal(
            name=APPROVED_TIME_FINANCE_PRINCIPAL_NAME
        ),
    )
    _procurement_financial_dispatcher = ProcurementFinancialDispatcher(
        session=session,
        outbox_service=_procurement_financial_outbox_service,
        uow_factory=project_management_services.finance_worker_uow_factory,
        consumer_factory=project_management_services.procurement_consumer_factory,
        principal_resolver=lambda: platform_services.service_principal_query.resolve_execution_principal(
            name=PROCUREMENT_FINANCE_PRINCIPAL_NAME
        ),
    )
    def dispatch_approved_time() -> None:
        _approved_time_financial_dispatcher.dispatch_pending()

    project_management_services.timesheet_period_transitions.set_approved_time_dispatcher(
        dispatch_approved_time
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
        platform=platform_services,
        project_management=project_management_services,
        integrations=IntegrationRuntimeBundle(
            module_registry=_module_registry,
            integration_resolver=_integration_resolver,
            time_financial_outbox_service=_time_financial_outbox_service,
            procurement_financial_outbox_service=_procurement_financial_outbox_service,
            approved_time_financial_dispatcher=_approved_time_financial_dispatcher,
            procurement_financial_dispatcher=_procurement_financial_dispatcher,
            accounting_connector_commands=build_accounting_configuration_commands(
                session=session,
                platform_services=platform_services,
                installed_adapters=accounting_adapter_ids,
            ),
        ),
        overview=global_overview_services,
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
