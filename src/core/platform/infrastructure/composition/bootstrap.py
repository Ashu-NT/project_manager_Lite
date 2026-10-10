"""Build the Platform service graph for the application composition root."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.orm import Session

from src.core.platform.access import (
    AccessControlService,
)
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.data_operations.runtime_tracking import (
    RuntimeExecutionService,
)
from src.core.platform.application.finance import FinancialPeriodService
from src.core.platform.application.history.activity import ActivityService
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.data_exchange import (
    MasterDataExchangeService,
)
from src.core.platform.application.master_data.department.department_service import (
    DepartmentService,
)
from src.core.platform.application.master_data.documents import (
    DocumentIntegrationService,
    DocumentService,
)
from src.core.platform.application.master_data.employee.employee_service import (
    EmployeeService,
)
from src.core.platform.application.master_data.org.organization_service import (
    OrganizationService,
)
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.application.notifications.notification_service import (
    NotificationService,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeApplicationService,
)
from src.core.platform.application.security.auth import AuthService
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceService,
    TenantRoleAdministrationService,
)
from src.core.platform.application.security.identity import ServicePrincipalService
from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.application.tenant.tenancy import (
    TenancyMode,
    TenantAdminService,
    TenantContextService,
    TenantMembershipService,
)
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.application.time_management.calendar.capacity.global_calendar_shim import (
    GlobalCalendarShim,
)
from src.core.platform.application.time_management.calendar.capacity.platform_calendar_resolver import (
    PlatformCalendarResolver,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import (
    WorkingTimeCalculator,
)
from src.core.platform.application.time_management.calendar.definitions.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.application.time_management.calendar.definitions.recurring_event_service import (
    RecurringEventService,
)
from src.core.platform.application.time_management.calendar.definitions.shift_pattern_service import (
    ShiftPatternService,
)
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import (
    WorkingRuleService,
)
from src.core.platform.application.time_management.calendar.platform_calendar_service import (
    PlatformCalendarService,
)
from src.core.platform.contract.repositories.master_data.org.contracts import (
    OrganizationRepository,
)
from src.core.platform.contract.repositories.master_data.party.contracts import (
    PartyRepository,
)
from src.core.platform.contract.repositories.master_data.site.contracts import (
    SiteRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.dependencies.approvals.approval import (
    build_approval_service,
)
from src.core.platform.infrastructure.composition.dependencies.finance.period import (
    build_financial_period_service,
)
from src.core.platform.infrastructure.composition.dependencies.history.services import (
    build_activity_service,
    build_enterprise_audit_service,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.catalog import (
    build_master_data_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.employee import (
    build_employee_service,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.exchange import (
    build_master_data_exchange_service,
)
from src.core.platform.infrastructure.composition.dependencies.master_data.organization import (
    build_organization_service,
)
from src.core.platform.infrastructure.composition.dependencies.notifications.delivery import (
    build_notification_service,
)
from src.core.platform.infrastructure.composition.dependencies.security.administration import (
    build_security_administration_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.security.auth import (
    build_auth_service,
)
from src.core.platform.infrastructure.composition.dependencies.security.governance import (
    build_role_governance_service,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.admin import (
    build_tenant_admin_service,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.context import (
    build_tenancy_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.membership import (
    build_tenant_membership_service,
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
from src.core.shared.events.view_invalidation import (
    ViewInvalidationChannel,
)
from src.infra.composition.persistence.repositories import RepositoryBundle
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


@dataclass(frozen=True)
class PlatformServiceBundle:
    session: Session
    user_session: UserSessionContext
    organization_repo: OrganizationRepository
    site_repo: SiteRepository
    party_repo: PartyRepository
    tenant_context_service: TenantContextService
    platform_view_invalidation_channel: ViewInvalidationChannel
   
    platform_transactional_dispatcher: InProcessTransactionalEventDispatcher
    platform_post_commit_bus: InProcessPostCommitEventBus
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_catalog_service: ModuleCatalogService
    auth_service: AuthService
    role_governance_service: RoleGovernanceService
    tenant_role_administration_service: TenantRoleAdministrationService
    organization_service: OrganizationService
    document_service: DocumentService
    document_integration_service: DocumentIntegrationService
    party_service: PartyService
    department_service: DepartmentService
    site_service: SiteService
    employee_service: EmployeeService
    master_data_exchange_service: MasterDataExchangeService
    runtime_execution_service: RuntimeExecutionService
    access_service: AccessControlService
    activity_service: ActivityService
    enterprise_audit_service: EnterpriseAuditService
    financial_period_service: FinancialPeriodService
    notification_service: NotificationService
    approval_service: ApprovalService
    platform_calendar_service: PlatformCalendarService
    working_rule_service: WorkingRuleService
    calendar_exception_service: CalendarExceptionService
    recurring_event_service: RecurringEventService
    shift_pattern_service: ShiftPatternService
    calendar_assignment_service: CalendarAssignmentService
    platform_calendar_resolver: PlatformCalendarResolver
    working_time_calculator: WorkingTimeCalculator
    tenant_admin_service: TenantAdminService
    tenant_membership_service: TenantMembershipService
    service_principal_service: ServicePrincipalService
    global_calendar_shim: GlobalCalendarShim
    runtime_security_configuration: RuntimeSecurityConfiguration


def build_platform_service_bundle(
    session: Session,
    repositories: RepositoryBundle,
    *,
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
    financial_period_service = build_financial_period_service(
        session=session,
        repositories=repositories,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
    )
    platform_view_invalidation_channel = InProcessViewInvalidationChannel()
    notification_service = build_notification_service(
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

    approval_service = build_approval_service(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    overview_rollup_reader = SqlAlchemyPlatformOverviewRollupReader(session)
    logger.debug("Creating Platform auth service and bootstrapping policy catalog")
    auth_service = build_auth_service(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
        overview_rollup_reader=overview_rollup_reader,
        security_configuration=security_configuration,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    logger.debug(
        "Platform auth policy catalog bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )

    organization_service = build_organization_service(
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
            organization_service=organization_service,
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
    tenant_admin_service = build_tenant_admin_service(
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
    document_service = master_data.document_service
    party_service = master_data.party_service
    site_service = master_data.site_service

    configure_session_rls_context(session, user_session=user_session)
    validate_postgresql_execution_role(session)
    logger.debug("Platform module catalog service created; bootstrapping defaults")
    modules = build_module_dependencies(
        session=session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
        organization_service=organization_service,
        view_invalidation_channel=platform_view_invalidation_channel,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    module_catalog_service = modules.module_catalog_service
    platform_runtime_application_service = modules.platform_runtime_application_service
    runtime_execution_service = modules.runtime_execution_service
    logger.debug(
        "Platform module catalog defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )

    scope_resolvers = build_scope_resolvers(
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
    )

    role_governance_service = build_role_governance_service(
        session=session,
        auth_service=auth_service,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        security_configuration=security_configuration,
        scope_resolvers=scope_resolvers,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    tenant_membership_service = build_tenant_membership_service(
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
        auth_service=auth_service,
        role_governance_service=role_governance_service,
        scope_resolvers=scope_resolvers,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    employee_service = build_employee_service(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        enterprise_audit_service=enterprise_audit_service,
        document_service=document_service,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    master_data_exchange_service = build_master_data_exchange_service(
        site_service=site_service,
        party_service=party_service,
        user_session=user_session,
    )

    calendar = build_calendar_dependencies(
        session=session,
        repositories=repositories,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        activity_service=activity_service,
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
        auth_service=auth_service,
        role_governance_service=role_governance_service,
        tenant_role_administration_service=security.tenant_role_administration_service,
        organization_service=organization_service,
        document_service=document_service,
        document_integration_service=master_data.document_integration_service,
        party_service=party_service,
        department_service=master_data.department_service,
        site_service=site_service,
        employee_service=employee_service,
        master_data_exchange_service=master_data_exchange_service,
        runtime_execution_service=runtime_execution_service,
        access_service=security.access_service,
        activity_service=activity_service,
        enterprise_audit_service=enterprise_audit_service,
        financial_period_service=financial_period_service,
        notification_service=notification_service,
        approval_service=approval_service,
        platform_calendar_service=calendar.platform_calendar_service,
        working_rule_service=calendar.working_rule_service,
        calendar_exception_service=calendar.calendar_exception_service,
        recurring_event_service=calendar.recurring_event_service,
        shift_pattern_service=calendar.shift_pattern_service,
        calendar_assignment_service=calendar.calendar_assignment_service,
        platform_calendar_resolver=calendar.platform_calendar_resolver,
        working_time_calculator=calendar.working_time_calculator,
        tenant_admin_service=tenant_admin_service,
        tenant_membership_service=tenant_membership_service,
        service_principal_service=security.service_principal_service,
        global_calendar_shim=calendar.global_calendar_shim,
        runtime_security_configuration=security_configuration,
    )
    logger.debug(
        "Platform service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return bundle


__all__ = ["PlatformServiceBundle", "build_platform_service_bundle"]
