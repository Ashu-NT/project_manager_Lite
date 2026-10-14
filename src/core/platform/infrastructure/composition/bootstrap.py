"""Build the Platform service graph for the application composition root."""

from __future__ import annotations

import logging
from collections.abc import Callable
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.tenant.tenancy import (
    TenancyMode,
)
from src.core.platform.contract.port.time_management.calendar.external_assignment_port import (
    ProjectCalendarAssignmentPort,
    ResourceCalendarAssignmentPort,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.core.platform.infrastructure.composition.dependencies.approvals.approval import (
    build_approval_handlers,
)
from src.core.platform.infrastructure.composition.dependencies.finance.period import (
    build_financial_period_handlers,
)
from src.core.platform.infrastructure.composition.dependencies.history.services import (
    build_activity_service,
    build_enterprise_audit_service,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.catalog import (
    build_master_data_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.employee import (
    build_employee_handlers,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.exchange import (
    build_master_data_exchange,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.organization import (
    build_organization_handlers,
)
from src.core.platform.infrastructure.composition.dependencies.notifications.delivery import (
    build_notification_handlers,
)
from src.core.platform.infrastructure.composition.dependencies.repositories import (
    PlatformRepositories,
    build_platform_repositories,
)
from src.core.platform.infrastructure.composition.dependencies.security.administration import (
    build_security_administration_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    build_auth_capabilities,
)
from src.core.platform.infrastructure.composition.dependencies.security.governance import (
    build_role_assignment_handler,
    build_role_governance_commands,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.admin import (
    build_tenant_admin_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.context import (
    build_tenancy_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.membership import (
    build_tenant_membership_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.modules import (
    build_module_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.time.calendar import (
    build_calendar_dependencies,
)
from src.core.platform.infrastructure.composition.events.approvals.view_invalidation import (
    register_approval_views,
)
from src.core.platform.infrastructure.composition.events.master_data.view_invalidation import (
    register_master_data_view_invalidation,
)
from src.core.platform.infrastructure.composition.events.notifications.approval_notifications import (
    register_platform_notification_policy,
)
from src.core.platform.infrastructure.composition.events.security.view_invalidation import (
    register_account_and_authorization_views,
    register_role_binding_views,
)
from src.core.platform.infrastructure.composition.events.tenancy.view_invalidation import (
    register_membership_views,
    register_organization_and_entitlement_views,
)
from src.core.platform.infrastructure.composition.registrations.security.scope_resolvers import (
    build_scope_resolvers,
)
from src.core.platform.infrastructure.composition.registrations.tenancy.local_defaults import (
    bootstrap_local_single_tenant_context,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.events.in_process_view_invalidation_channel import (
    InProcessViewInvalidationChannel,
)
from src.infra.persistence.db.postgresql_rls import (
    configure_session_rls_context,
    validate_postgresql_execution_role,
)
from src.infra.platform.security_config import (
    RuntimeSecurityConfiguration,
    load_runtime_security_configuration,
)

logger = logging.getLogger(__name__)



def build_platform_service_bundle(
    session: Session,
    repositories: PlatformRepositories,
    *,
    project_assignment_repo: ProjectCalendarAssignmentPort[Any] | None = None,
    resource_assignment_repo: ResourceCalendarAssignmentPort[Any] | None = None,
    runtime_security_configuration: RuntimeSecurityConfiguration | None = None,
    notification_recipient_policy: Callable[[Session, object], bool] | None = None,
) -> PlatformServiceBundle:
    started = perf_counter()
    logger.debug("Platform service bundle build begin")
    security_configuration = (
        runtime_security_configuration or load_runtime_security_configuration()
    )
    logger.info(
        "Runtime security configuration deployment_environment=%s tenancy_mode=%s",
        security_configuration.deployment_environment.value,
        security_configuration.tenancy_mode.value,
    )
    tenancy = build_tenancy_dependencies(
        session=session,
        repositories=repositories,
        security_configuration=security_configuration,
    )
    user_session = tenancy.user_session
    tenant_context_service = tenancy.tenant_context_service
    enterprise_audit_service = build_enterprise_audit_service(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    financial_period_commands, financial_period_queries = build_financial_period_handlers(
        session=session,
        repositories=repositories,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
    )
    platform_view_invalidation_channel = InProcessViewInvalidationChannel()
    notifications = build_notification_handlers(
        session=session,
        repositories=repositories,
        user_session=user_session,
        view_invalidation_channel=platform_view_invalidation_channel,
        recipient_policy=notification_recipient_policy,
    )
    activity_service = build_activity_service(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    platform_transactional_dispatcher = InProcessTransactionalEventDispatcher()
    register_platform_notification_policy(platform_transactional_dispatcher)
    platform_post_commit_bus = InProcessPostCommitEventBus()

    register_organization_and_entitlement_views(
        platform_post_commit_bus, platform_view_invalidation_channel
    )
    register_role_binding_views(platform_post_commit_bus, platform_view_invalidation_channel)
    register_membership_views(platform_post_commit_bus, platform_view_invalidation_channel)
    register_account_and_authorization_views(
        platform_post_commit_bus, platform_view_invalidation_channel
    )
    register_approval_views(platform_post_commit_bus, platform_view_invalidation_channel)

    register_master_data_view_invalidation(
        platform_post_commit_bus, platform_view_invalidation_channel
    )

    approval = build_approval_handlers(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    overview_rollup_reader = SqlAlchemyPlatformOverviewRollupReader(session)
    logger.debug("Creating Platform auth handlers and bootstrapping policy catalog")
    auth = build_auth_capabilities(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        security_configuration=security_configuration,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    logger.debug(
        "Platform auth policy catalog bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )

    organization = build_organization_handlers(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
        overview_rollup_reader=overview_rollup_reader,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    if security_configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT:
        logger.debug("Bootstrapping explicit local single-tenant defaults")
        bootstrap_local_single_tenant_context(
            session=session,
            repositories=repositories,
            user_session=user_session,
            organization_commands=organization.commands,
        )
    else:
        logger.info(
            "SaaS startup skipped default tenant, organization, context, and "
            "user-membership bootstrap"
        )

    logger.debug(
        "Platform organization defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    tenant_admin = build_tenant_admin_dependencies(
        session=session,
        repositories=repositories,
        user_session=user_session,
    )
    master_data = build_master_data_dependencies(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
        overview_rollup_reader=overview_rollup_reader,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )

    configure_session_rls_context(session, user_session=user_session)
    validate_postgresql_execution_role(session)
    logger.debug("Platform module catalog service created; bootstrapping defaults")
    modules = build_module_dependencies(
        session=session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        organization=organization,
        view_invalidation_channel=platform_view_invalidation_channel,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    module_catalog_service = modules.module_catalog_service
    module_entitlement_commands = modules.module_entitlement_commands
    platform_runtime_application_service = modules.platform_runtime_application_service
    runtime_execution_commands = modules.runtime_execution_commands
    logger.debug(
        "Platform module catalog defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )

    scope_resolvers = build_scope_resolvers(
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
    )

    role_governance_commands = build_role_governance_commands(
        session=session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        security_configuration=security_configuration,
        scope_resolvers=scope_resolvers,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    tenant_membership = build_tenant_membership_dependencies(
        session=session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        scope_resolvers=scope_resolvers,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    security = build_security_administration_dependencies(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
        auth=auth,
        role_governance_commands=role_governance_commands,
        scope_resolvers=scope_resolvers,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    employee = build_employee_handlers(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        document_commands=master_data.document_commands,
        document_query=master_data.document_query,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    master_data_exchange = build_master_data_exchange(
        site_commands=master_data.site_commands,
        site_query=master_data.site_query,
        party_commands=master_data.party_commands,
        party_query=master_data.party_query,
        user_session=user_session,
    )

    calendar = build_calendar_dependencies(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        activity_service=activity_service,
        project_assignment_repo=project_assignment_repo,
        resource_assignment_repo=resource_assignment_repo,
    )

    bundle = PlatformServiceBundle(
        session=session,
        user_session=user_session,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        party_repo=repositories.party_repo,
        tenant_context_service=tenant_context_service,
        platform_view_invalidation_channel=platform_view_invalidation_channel,
        platform_transactional_dispatcher=platform_transactional_dispatcher,
        platform_post_commit_bus=platform_post_commit_bus,
        platform_runtime_application_service=platform_runtime_application_service,
        module_catalog_service=module_catalog_service,
        module_entitlement_commands=module_entitlement_commands,
        auth=auth,
        role_assignment_commands=build_role_assignment_handler(
            repositories=repositories,
            auth=auth,
            role_governance_commands=role_governance_commands,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        ),
        role_governance_commands=role_governance_commands,
        tenant_role_commands=security.tenant_role_commands,
        tenant_role_queries=security.tenant_role_queries,
        organization_commands=organization.commands,
        organization_lifecycle=organization.lifecycle,
        organization_query=organization.query,
        document_access_policy=master_data.document_access_policy,
        document_commands=master_data.document_commands,
        document_structure_commands=master_data.document_structure_commands,
        document_query=master_data.document_query,
        document_attachment_commands=master_data.document_attachment_commands,
        document_attachment_query=master_data.document_attachment_query,
        party_commands=master_data.party_commands,
        party_query=master_data.party_query,
        department_commands=master_data.department_commands,
        department_query=master_data.department_query,
        site_commands=master_data.site_commands,
        site_query=master_data.site_query,
        employee_commands=employee.commands,
        employee_query=employee.query,
        employee_document_commands=employee.documents,
        master_data_import_runtime=master_data_exchange.import_runtime,
        master_data_export_runtime=master_data_exchange.export_runtime,
        runtime_execution_commands=runtime_execution_commands,
        runtime_execution_query=modules.runtime_execution_query,
        access_service=security.access_service,
        activity_service=activity_service,
        enterprise_audit_service=enterprise_audit_service,
        financial_period_commands=financial_period_commands,
        financial_period_queries=financial_period_queries,
        notification_commands=notifications.commands,
        notification_queries=notifications.queries,
        approval_commands=approval.commands,
        approval_queries=approval.queries,
        approval_participants=approval.participants,
        platform_calendar_service=calendar.platform_calendar_service,
        working_rule_service=calendar.working_rule_service,
        calendar_exception_service=calendar.calendar_exception_service,
        recurring_event_service=calendar.recurring_event_service,
        shift_pattern_service=calendar.shift_pattern_service,
        calendar_assignment_service=calendar.calendar_assignment_service,
        platform_calendar_resolver=calendar.platform_calendar_resolver,
        working_time_calculator=calendar.working_time_calculator,
        tenant_admin_queries=tenant_admin.tenant_admin_queries,
        tenant_lifecycle_commands=tenant_admin.tenant_lifecycle_commands,
        tenant_invitation_commands=tenant_membership.tenant_invitation_commands,
        tenant_membership_lifecycle_commands=tenant_membership.tenant_membership_lifecycle_commands,
        tenant_membership_queries=tenant_membership.tenant_membership_queries,
        service_principal_commands=security.service_principal_commands,
        service_principal_query=security.service_principal_query,
        api_key_authentication=security.api_key_authentication,
        global_calendar_shim=calendar.global_calendar_shim,
        runtime_security_configuration=security_configuration,
    )
    logger.debug(
        "Platform service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return bundle


__all__ = ["build_platform_repositories", "build_platform_service_bundle"]
