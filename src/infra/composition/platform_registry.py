from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.orm import Session

from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from src.core.platform.modules import (
    DEFAULT_ENTERPRISE_MODULES,
    ModuleCatalogService,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
)
from src.core.platform.access import AccessControlService, ScopedRolePolicy, ScopedRolePolicyRegistry
from src.core.platform.activity import ActivityService
from src.core.platform.approval import ApprovalService
from src.core.platform.audit import EnterpriseAuditService
from src.core.platform.notifications import NotificationService
from src.core.platform.auth import (
    AuthService,
    RoleGovernanceService,
    TenantRoleAdministrationService,
)
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.documents import DocumentIntegrationService, DocumentService
from src.core.platform.data_exchange import MasterDataExchangeService
from src.core.platform.department import DepartmentService
from src.core.platform.employee import EmployeeService
from src.core.platform.org import Organization, OrganizationRepository, OrganizationService
from src.core.platform.site import SiteRepository, SiteService
from src.core.platform.site.access_policy import (
    SITE_SCOPE_ROLE_CHOICES,
    normalize_site_scope_role,
    resolve_site_scope_permissions,
)
from src.core.platform.tenancy import (
    TenantAdminService,
    TenantMembershipService,
    TenantContextService,
    TenancyMode,
    Tenant,
    UserTenantMembership,
    build_tenant_context_policy,
)
from src.core.platform.party import PartyService
from src.core.platform.party.contracts import PartyRepository
from src.core.platform.runtime_tracking import RuntimeExecutionService
from src.core.platform.calendar.application.enterprise_calendar_service import EnterpriseCalendarService
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.application.calendar_exception_service import CalendarExceptionService
from src.core.platform.calendar.application.recurring_event_service import RecurringEventService
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.application.calendar_assignment_service import CalendarAssignmentService
from src.core.platform.calendar.application.enterprise_calendar_resolver import EnterpriseCalendarResolver
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator
from src.core.platform.calendar.application.global_calendar_shim import GlobalCalendarShim
from src.core.platform.infrastructure.persistence.repositories.modules import SqlAlchemyModuleEntitlementRepository
from src.core.platform.infrastructure.persistence.repositories.runtime_tracking import SqlAlchemyRuntimeExecutionRepository
from src.infra.composition.repositories import RepositoryBundle
from src.infra.platform.operational_support import current_trace_id
from src.infra.platform.security_audit_recorder import (
    DurableSecurityDenialRecorder,
)
from src.infra.platform.security_config import (
    RuntimeSecurityConfiguration,
    load_runtime_security_configuration,
)


logger = logging.getLogger(__name__)


def _bootstrap_local_single_tenant_context(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    organization_service: OrganizationService,
) -> None:
    """Preserve explicit local-desktop defaults outside hosted SaaS mode."""
    default_tenant = repositories.tenant_repo.get_default()
    if default_tenant is None:
        existing_organizations = repositories.organization_repo.list_all()
        tenant_code = (
            existing_organizations[0].organization_code
            if existing_organizations
            else "DEFAULT"
        )
        tenant_name = (
            existing_organizations[0].display_name
            if existing_organizations
            else "Default Tenant"
        )
        default_tenant = Tenant.create(
            tenant_code=tenant_code,
            display_name=tenant_name,
        )
        repositories.tenant_repo.add(default_tenant)
        session.flush()
        for organization in existing_organizations:
            if not organization.tenant_id:
                organization.tenant_id = default_tenant.id
                repositories.organization_repo.update(organization)
        session.commit()
        logger.debug(
            "Platform local default tenant bootstrapped tenant_id=%s",
            default_tenant.id,
        )

    user_session.set_active_tenant_id(default_tenant.id)
    organization_service.bootstrap_defaults()

    organizations = repositories.organization_repo.list_for_tenant(
        default_tenant.id,
        active_only=True,
    )
    if not organizations:
        organizations = repositories.organization_repo.list_for_tenant(
            default_tenant.id
        )
    if organizations:
        user_session.set_active_organization_id(organizations[0].id)

    for user in repositories.user_repo.list_all():
        if repositories.user_tenant_repo.get(
            user.id,
            default_tenant.id,
        ) is not None:
            continue
        repositories.user_tenant_repo.add(
            UserTenantMembership.create(
                user_id=user.id,
                tenant_id=default_tenant.id,
                tenant_role="member",
            )
        )
    session.commit()


@dataclass(frozen=True)
class PlatformServiceBundle:
    session: Session
    user_session: UserSessionContext
    organization_repo: OrganizationRepository
    site_repo: SiteRepository
    party_repo: PartyRepository
    tenant_context_service: TenantContextService
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_runtime_service: ModuleRuntimeService
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
    notification_service: NotificationService
    approval_service: ApprovalService
    enterprise_calendar_service: EnterpriseCalendarService
    working_rule_service: WorkingRuleService
    calendar_exception_service: CalendarExceptionService
    recurring_event_service: RecurringEventService
    shift_pattern_service: ShiftPatternService
    calendar_assignment_service: CalendarAssignmentService
    enterprise_calendar_resolver: EnterpriseCalendarResolver
    working_time_calculator: WorkingTimeCalculator
    tenant_admin_service: TenantAdminService
    tenant_membership_service: TenantMembershipService
    global_calendar_shim: GlobalCalendarShim
    runtime_security_configuration: RuntimeSecurityConfiguration


def build_platform_service_bundle(
    session: Session,
    repositories: RepositoryBundle,
    *,
    runtime_security_configuration: RuntimeSecurityConfiguration | None = None,
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
    user_session = UserSessionContext()
    security_denial_recorder = DurableSecurityDenialRecorder.for_session(
        session,
        trace_id_provider=current_trace_id,
    )
    user_session.set_security_denial_listener(
        security_denial_recorder.record
    )
    tenant_context_service = TenantContextService(
        tenant_repo=repositories.tenant_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        user_tenant_repo=repositories.user_tenant_repo,
        context_policy=build_tenant_context_policy(
            security_configuration.tenancy_mode
        ),
    )
    # Wire _tenant_context_service on all repos that support it.
    for _field_name in repositories.__dataclass_fields__:
        _repo = getattr(repositories, _field_name)
        if hasattr(_repo, "_tenant_context_service"):
            _repo._tenant_context_service = tenant_context_service
    enterprise_audit_service = EnterpriseAuditService(
        session=session,
        audit_repo=repositories.audit_entry_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    notification_service = NotificationService(
        session=session,
        notification_repo=repositories.notification_repo,
        user_session=user_session,
    )
    activity_service = ActivityService(
        session=session,
        activity_repo=repositories.activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    approval_service = ApprovalService(
        session=session,
        approval_repo=repositories.approval_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
    )
    auth_service = AuthService(
        session=session,
        user_repo=repositories.user_repo,
        role_repo=repositories.role_repo,
        permission_repo=repositories.permission_repo,
        role_permission_repo=repositories.role_permission_repo,
        auth_session_repo=repositories.auth_session_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        security_audit_repo=repositories.audit_entry_repo,
        user_tenant_repo=repositories.user_tenant_repo,
        tenant_context_service=tenant_context_service,
        request_id_provider=current_trace_id,
        role_binding_repo=repositories.role_binding_repo,
        canonical_scope_tenant_resolvers={
            "organization": lambda tenant_id, organization_id: (
                repositories.organization_repo.get_for_tenant(
                    organization_id,
                    tenant_id,
                )
                is not None
            ),
            "site": lambda tenant_id, site_id: (
                tenant_context_service.require_active_tenant_id(
                    operation_label="validate site access scope"
                )
                == tenant_id
                and repositories.site_repo.get(site_id) is not None
            ),
        },
        allow_platform_customer_context=(
            security_configuration.tenancy_mode
            is TenancyMode.LOCAL_SINGLE_TENANT
        ),
    )
    tenant_context_service.set_principal_rebuilder(
        auth_service.rebuild_current_principal_for_context
    )
    tenant_context_service.set_context_switch_committer(
        auth_service.commit_context_switch
    )
    user_session.set_validator(auth_service.validate_session_principal)
    user_session.set_context_listener(auth_service.persist_session_context)
    logger.debug("Platform auth service created; bootstrapping policy catalog")
    if security_configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT:
        auth_service.bootstrap_defaults()
    else:
        auth_service.bootstrap_policy_catalog()
    logger.debug(
        "Platform auth policy catalog bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )

    organization_service = OrganizationService(
        session=session,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
    )

    if security_configuration.tenancy_mode is TenancyMode.LOCAL_SINGLE_TENANT:
        logger.debug("Bootstrapping explicit local single-tenant defaults")
        _bootstrap_local_single_tenant_context(
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
    tenant_admin_service = TenantAdminService(
        session=session,
        tenant_repo=repositories.tenant_repo,
        user_tenant_repo=repositories.user_tenant_repo,
        user_session=user_session,
        platform_event_repo=repositories.platform_event_repo,
    )
    tenant_membership_service = TenantMembershipService(
        session=session,
        tenant_repo=repositories.tenant_repo,
        membership_repo=repositories.user_tenant_repo,
        user_repo=repositories.user_repo,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
        auth_session_repo=repositories.auth_session_repo,
        audit_repo=repositories.audit_entry_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        notification_service=notification_service,
    )
    document_service = DocumentService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
    )
    document_integration_service = DocumentIntegrationService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
    )
    party_service = PartyService(
        session=session,
        party_repo=repositories.party_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
    )
    site_service = SiteService(
        session=session,
        site_repo=repositories.site_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
    )
    department_service = DepartmentService(
        session=session,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        employee_repo=repositories.employee_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
    )

    def _active_organization() -> Organization | None:
        return tenant_context_service.get_active_organization()

    def _active_organization_id() -> str | None:
        return tenant_context_service.get_active_organization_id()

    module_entitlement_repo = SqlAlchemyModuleEntitlementRepository(
        session,
        organization_id_provider=_active_organization_id,
    )
    module_catalog_service = ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        enabled_codes=parse_enabled_module_codes(os.getenv("PM_ENABLED_MODULES")),
        licensed_codes=parse_licensed_module_codes(
            os.getenv("PM_LICENSED_MODULES")
            if os.getenv("PM_LICENSED_MODULES") is not None
            else os.getenv("PM_ENABLED_MODULES")
        ),
        entitlement_repo=module_entitlement_repo,
        session=session,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        organization_context_provider=_active_organization,
    )
    logger.debug("Platform module catalog service created; bootstrapping defaults")
    module_catalog_service.bootstrap_defaults()
    logger.debug(
        "Platform module catalog defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    module_runtime_service = ModuleRuntimeService(module_catalog_service)
    platform_runtime_application_service = PlatformRuntimeApplicationService(
        module_runtime_service=module_runtime_service,
        organization_service=organization_service,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    runtime_execution_service = RuntimeExecutionService(
        runtime_execution_repo=SqlAlchemyRuntimeExecutionRepository(session),
        user_session=user_session,
    )
    scope_exists_resolvers = {
        "organization": lambda tenant_id, organization_id: (
            repositories.organization_repo.get_for_tenant(
                organization_id,
                tenant_id,
            )
            is not None
        ),
        "site": lambda tenant_id, site_id: (
            tenant_context_service.require_active_tenant_id(
                operation_label="validate site access scope"
            )
            == tenant_id
            and repositories.site_repo.get(site_id) is not None
        ),
    }
    role_governance_service = RoleGovernanceService(
        session=session,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
        delegation_repo=repositories.role_delegation_policy_repo,
        role_permission_repo=repositories.role_permission_repo,
        permission_repo=repositories.permission_repo,
        user_repo=repositories.user_repo,
        tenant_repo=repositories.tenant_repo,
        membership_repo=repositories.user_tenant_repo,
        audit_repo=repositories.audit_entry_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        scope_exists_resolvers=scope_exists_resolvers,
        allow_platform_customer_context=(
            security_configuration.tenancy_mode
            is TenancyMode.LOCAL_SINGLE_TENANT
        ),
    )
    auth_service.set_role_governance_service(role_governance_service)
    access_service = AccessControlService(
        session=session,
        user_repo=repositories.user_repo,
        auth_service=auth_service,
        policy_registry=ScopedRolePolicyRegistry(
            (
                ScopedRolePolicy(
                    scope_type="site",
                    role_choices=SITE_SCOPE_ROLE_CHOICES,
                    normalize_role=normalize_site_scope_role,
                    resolve_permissions=resolve_site_scope_permissions,
                ),
            )
        ),
        scope_exists_resolvers=scope_exists_resolvers,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        user_tenant_repo=repositories.user_tenant_repo,
        tenant_context_service=tenant_context_service,
        role_governance_service=role_governance_service,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
    )
    tenant_role_administration_service = TenantRoleAdministrationService(
        session=session,
        role_repo=repositories.role_repo,
        role_binding_repo=repositories.role_binding_repo,
        role_permission_repo=repositories.role_permission_repo,
        permission_repo=repositories.permission_repo,
        auth_session_repo=repositories.auth_session_repo,
        tenant_repo=repositories.tenant_repo,
        membership_repo=repositories.user_tenant_repo,
        audit_repo=repositories.audit_entry_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    employee_service = EmployeeService(
        session=session,
        employee_repo=repositories.employee_repo,
        resource_repo=repositories.resource_repo,
        site_repo=repositories.site_repo,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
    )
    master_data_exchange_service = MasterDataExchangeService(
        site_service=site_service,
        party_service=party_service,
        user_session=user_session,
    )

    # --- Enterprise calendar services ---
    working_time_calculator = WorkingTimeCalculator()
    enterprise_calendar_service = EnterpriseCalendarService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        organization_repo=repositories.organization_repo,
        rule_repo=repositories.calendar_working_rule_repo,
        exception_repo=repositories.calendar_exception_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    working_rule_service = WorkingRuleService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        rule_repo=repositories.calendar_working_rule_repo,
        user_session=user_session,
    )
    calendar_exception_service = CalendarExceptionService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        exception_repo=repositories.calendar_exception_repo,
        user_session=user_session,
    )
    recurring_event_service = RecurringEventService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        event_repo=repositories.calendar_recurring_event_repo,
        user_session=user_session,
    )
    shift_pattern_service = ShiftPatternService(
        session=session,
        pattern_repo=repositories.shift_pattern_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    calendar_assignment_service = CalendarAssignmentService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        project_assignment_repo=repositories.project_calendar_assignment_repo,
        resource_assignment_repo=repositories.resource_calendar_assignment_repo,
        user_session=user_session,
    )

    def _get_active_org_id() -> str:
        return tenant_context_service.get_active_organization_id() or ""

    enterprise_calendar_resolver = EnterpriseCalendarResolver(
        organization_id=_get_active_org_id(),
        calendar_repo=repositories.platform_calendar_repo,
        rule_repo=repositories.calendar_working_rule_repo,
        exception_repo=repositories.calendar_exception_repo,
        recurring_repo=repositories.calendar_recurring_event_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        project_assignment_repo=repositories.project_calendar_assignment_repo,
        resource_assignment_repo=repositories.resource_calendar_assignment_repo,
        calculator=working_time_calculator,
    )
    global_calendar_shim = GlobalCalendarShim(resolver=enterprise_calendar_resolver)
    # Bootstrap global calendar. After the Alembic migration drops legacy tables,
    # working_calendar_repo will not be passed — the enterprise tables already hold the data.
    try:
        org = tenant_context_service.get_active_organization()
        if org:
            logger.debug("Ensuring enterprise global calendar organization_id=%s", org.id)
            enterprise_calendar_service.ensure_global_calendar(org.id)
            logger.debug("Enterprise global calendar ensured organization_id=%s", org.id)
    except Exception:
        logger.exception("Enterprise global calendar bootstrap failed; continuing startup")

    bundle = PlatformServiceBundle(
        session=session,
        user_session=user_session,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        party_repo=repositories.party_repo,
        tenant_context_service=tenant_context_service,
        platform_runtime_application_service=platform_runtime_application_service,
        module_runtime_service=module_runtime_service,
        module_catalog_service=module_catalog_service,
        auth_service=auth_service,
        role_governance_service=role_governance_service,
        tenant_role_administration_service=(
            tenant_role_administration_service
        ),
        organization_service=organization_service,
        document_service=document_service,
        document_integration_service=document_integration_service,
        party_service=party_service,
        department_service=department_service,
        site_service=site_service,
        employee_service=employee_service,
        master_data_exchange_service=master_data_exchange_service,
        runtime_execution_service=runtime_execution_service,
        access_service=access_service,
        activity_service=activity_service,
        enterprise_audit_service=enterprise_audit_service,
        notification_service=notification_service,
        approval_service=approval_service,
        enterprise_calendar_service=enterprise_calendar_service,
        working_rule_service=working_rule_service,
        calendar_exception_service=calendar_exception_service,
        recurring_event_service=recurring_event_service,
        shift_pattern_service=shift_pattern_service,
        calendar_assignment_service=calendar_assignment_service,
        enterprise_calendar_resolver=enterprise_calendar_resolver,
        working_time_calculator=working_time_calculator,
        tenant_admin_service=tenant_admin_service,
        tenant_membership_service=tenant_membership_service,
        global_calendar_shim=global_calendar_shim,
        runtime_security_configuration=security_configuration,
    )
    logger.debug(
        "Platform service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return bundle


__all__ = ["PlatformServiceBundle", "build_platform_service_bundle"]
