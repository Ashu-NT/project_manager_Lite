from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from time import perf_counter

from sqlalchemy.orm import Session, sessionmaker

from src.core.platform.application.platform_runtime import PlatformRuntimeApplicationService
from src.core.platform.domain.tenant.modules import (
    DEFAULT_ENTERPRISE_MODULES,
    parse_enabled_module_codes,
    parse_licensed_module_codes,
)
from src.core.platform.application.tenant.modules import ModuleCatalogService
from src.core.platform.access import AccessControlService, ScopedRolePolicy, ScopedRolePolicyRegistry
from src.core.platform.application.history.activity import ActivityService
from src.core.platform.application.approval.approval_service import ApprovalService
from src.core.platform.application.approval.event_handlers.view_invalidation import (
    build_approval_view_invalidation_handler,
)
from src.core.platform.domain.approval.events import (
    ApprovalApproved,
    ApprovalRejected,
    ApprovalRequested,
)
from src.core.platform.infrastructure.persistence.uow.approval_unit_of_work import (
    SqlAlchemyPlatformUnitOfWorkFactory,
)
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.events.in_process_view_invalidation_channel import InProcessViewInvalidationChannel
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)
from src.infra.time.system_clock import SystemClock
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.finance import FinancialPeriodService
from src.core.platform.application.events.notifications.notification_service import NotificationService
from src.core.platform.application.security.auth import AuthService
from src.core.platform.application.security.authorization.roles import (
    RoleGovernanceService,
    TenantRoleAdministrationService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.application.master_data.documents import DocumentIntegrationService, DocumentService
from src.core.platform.application.master_data.data_exchange import MasterDataExchangeService
from src.core.platform.application.master_data.department.department_service import DepartmentService
from src.core.platform.application.master_data.employee.employee_service import EmployeeService
from src.core.platform.infrastructure.persistence.read.master_data.employee.employee_headcount_reader import (
    SqlAlchemyEmployeeHeadcountReader,
)
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.core.platform.application.master_data.org.organization_service import OrganizationService
from src.core.platform.application.master_data.org.event_handlers.view_invalidation import (
    build_organization_created_view_invalidation_handler,
    build_organization_profile_view_invalidation_handler,
)
from src.core.platform.domain.master_data.org.events import (
    OrganizationCreated,
    OrganizationDisabled,
    OrganizationEnabled,
    OrganizationProfileUpdated,
)
from src.core.platform.application.master_data.employee.event_handlers.view_invalidation import (
    build_employee_list_view_invalidation_handler,
)
from src.core.platform.domain.master_data.employee.events import (
    EmployeeCreated,
    EmployeeProfileUpdated,
)
from src.core.platform.application.master_data.department.event_handlers.view_invalidation import (
    build_department_list_view_invalidation_handler,
)
from src.core.platform.domain.master_data.department.events import (
    DepartmentCreated,
    DepartmentProfileUpdated,
)
from src.core.platform.application.master_data.site.event_handlers.view_invalidation import (
    build_site_list_view_invalidation_handler,
)
from src.core.platform.domain.master_data.site.events import (
    SiteCreated,
    SiteDisabled,
    SiteEnabled,
    SiteProfileUpdated,
)
from src.core.platform.application.master_data.party.event_handlers.view_invalidation import (
    build_party_list_view_invalidation_handler,
)
from src.core.platform.domain.master_data.party.events import (
    PartyCreated,
    PartyProfileUpdated,
)
from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
    build_document_list_view_invalidation_handler,
    build_document_structure_list_view_invalidation_handler,
)
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentProfileUpdated,
    DocumentStructureCreated,
    DocumentStructureProfileUpdated,
)
from src.core.platform.application.tenant.modules.event_handlers.view_invalidation import (
    build_module_entitlement_view_invalidation_handler,
)
from src.core.platform.domain.tenant.modules.events import (
    ModuleDisabled,
    ModuleEnabled,
    ModuleLicenseRevoked,
    ModuleLicensed,
    ModuleLifecycleTransitioned,
)
from src.core.platform.application.security.authorization.roles.event_handlers.view_invalidation import (
    build_role_binding_view_invalidation_handler,
)
from src.core.platform.application.tenant.tenancy.event_handlers.view_invalidation import (
    build_tenant_membership_view_invalidation_handler,
)
from src.core.platform.domain.tenant.tenancy.events import (
    TenantMembershipActivated,
    TenantMembershipReactivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
)
from src.core.platform.domain.security.authorization.roles.events import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
from src.core.platform.infrastructure.persistence.uow.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.department_unit_of_work import (
    SqlAlchemyDepartmentUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.site_unit_of_work import (
    SqlAlchemySiteUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.employee_unit_of_work import (
    SqlAlchemyEmployeeUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.party_unit_of_work import (
    SqlAlchemyPartyUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.document_unit_of_work import (
    SqlAlchemyDocumentUnitOfWorkFactory,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.resources.resource import (
    SqlAlchemyResourceRepository,
)
from src.core.platform.infrastructure.persistence.uow.platform_provisioning_unit_of_work import (
    SqlAlchemyPlatformProvisioningUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.module_entitlement_unit_of_work import (
    SqlAlchemyModuleEntitlementUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.role_governance_unit_of_work import (
    SqlAlchemyRoleGovernanceUnitOfWorkFactory,
)
from src.core.platform.infrastructure.persistence.uow.tenant_membership_unit_of_work import (
    SqlAlchemyTenantMembershipUnitOfWorkFactory,
)
from src.core.platform.contract.repositories.master_data.org.contracts import OrganizationRepository
from src.core.platform.infrastructure.persistence.repositories.master_data.org.org import (
    SqlAlchemyOrganizationRepository,
)
from src.core.platform.domain.master_data.org import Organization
from src.core.platform.application.master_data.site.site_service import SiteService
from src.core.platform.contract.repositories.master_data.site.contracts import SiteRepository
from src.core.platform.infrastructure.persistence.repositories.master_data.site.sites import (
    SqlAlchemySiteRepository,
)
from src.core.platform.domain.master_data.site.access_policy import (
    SITE_SCOPE_ROLE_CHOICES,
    normalize_site_scope_role,
    resolve_site_scope_permissions,
)
from src.core.platform.domain.master_data.org.access_policy import (
    ORGANIZATION_SCOPE_ROLE_CHOICES,
    normalize_organization_scope_role,
    resolve_organization_scope_permissions,
)
from src.core.platform.domain.tenant.tenancy import Tenant, UserTenantMembership
from src.core.platform.application.tenant.tenancy import (
    TenantAdminService,
    TenantMembershipService,
    TenantContextService,
    TenancyMode,
    build_tenant_context_policy,
)
from src.core.platform.application.master_data.party.party_service import PartyService
from src.core.platform.contract.repositories.master_data.party.contracts import PartyRepository
from src.core.platform.application.data_operations.runtime_tracking import RuntimeExecutionService
from src.core.platform.application.security.identity import ServicePrincipalService
from src.core.platform.application.time_management.calendar.enterprise_calendar_service import EnterpriseCalendarService
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import WorkingRuleService
from src.core.platform.application.time_management.calendar.definitions.calendar_exception_service import CalendarExceptionService
from src.core.platform.application.time_management.calendar.definitions.recurring_event_service import RecurringEventService
from src.core.platform.application.time_management.calendar.definitions.shift_pattern_service import ShiftPatternService
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import CalendarAssignmentService
from src.core.platform.application.time_management.calendar.capacity.enterprise_calendar_resolver import EnterpriseCalendarResolver
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import WorkingTimeCalculator
from src.core.platform.application.time_management.calendar.capacity.global_calendar_shim import GlobalCalendarShim
from src.core.platform.infrastructure.persistence.repositories.tenant.modules.modules import SqlAlchemyModuleEntitlementRepository
from src.core.platform.infrastructure.persistence.read.tenant.modules.module_entitlement_reader import SqlAlchemyModuleEntitlementReader
from src.core.platform.infrastructure.persistence.repositories.data_operations.runtime_tracking.runtime_tracking import SqlAlchemyRuntimeExecutionRepository
from src.infra.composition.repositories import RepositoryBundle
from src.infra.platform.operational_support import current_trace_id
from src.infra.platform.security_audit_recorder import (
    DurableSecurityDenialRecorder,
)
from src.infra.platform.security_config import (
    RuntimeSecurityConfiguration,
    load_runtime_security_configuration,
)
from src.infra.persistence.db.postgresql_rls import (
    configure_session_rls_context,
    validate_postgresql_execution_role,
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
        enabled_only=True,
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
    platform_view_invalidation_channel: ViewInvalidationChannel
   
    platform_transactional_dispatcher: TransactionalEventDispatcher
    platform_post_commit_bus: PostCommitEventPublisher
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
    service_principal_service: ServicePrincipalService
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
    financial_period_service = FinancialPeriodService(
        session=session,
        period_repo=repositories.financial_period_repo,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
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
    platform_transactional_dispatcher = InProcessTransactionalEventDispatcher()
    platform_post_commit_bus = InProcessPostCommitEventBus()
    platform_view_invalidation_channel = InProcessViewInvalidationChannel()

    platform_post_commit_bus.subscribe(
        OrganizationCreated,
        build_organization_created_view_invalidation_handler(platform_view_invalidation_channel),
    )
    _organization_profile_view_invalidation_handler = build_organization_profile_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _organization_profile_event_type in (
        OrganizationProfileUpdated,
        OrganizationEnabled,
        OrganizationDisabled,
    ):
        platform_post_commit_bus.subscribe(
            _organization_profile_event_type, _organization_profile_view_invalidation_handler
        )

    _module_entitlement_view_invalidation_handler = build_module_entitlement_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _module_entitlement_event_type in (
        ModuleLicensed,
        ModuleLicenseRevoked,
        ModuleEnabled,
        ModuleDisabled,
        ModuleLifecycleTransitioned,
    ):
        platform_post_commit_bus.subscribe(
            _module_entitlement_event_type, _module_entitlement_view_invalidation_handler
        )

    _role_binding_view_invalidation_handler = build_role_binding_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _role_binding_event_type in (RoleBindingAssigned, RoleBindingRevoked):
        platform_post_commit_bus.subscribe(
            _role_binding_event_type, _role_binding_view_invalidation_handler
        )

    # P5D-3: direct Qt cutover for Tenant Membership, mirroring the Organization/RoleBinding
    # precedent above -- no legacy `auth_changed` bridge. All four membership events collapse
    # onto the SAME single mapping handler (every real UI consumer re-reads the whole
    # membership-backed user list/rollup, never one membership row at a time).
    _tenant_membership_view_invalidation_handler = build_tenant_membership_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _tenant_membership_event_type in (
        TenantMembershipActivated,
        TenantMembershipSuspended,
        TenantMembershipReactivated,
        TenantMembershipRemoved,
    ):
        platform_post_commit_bus.subscribe(
            _tenant_membership_event_type, _tenant_membership_view_invalidation_handler
        )

    # Approval-P3: direct Qt cutover for Approval, mirroring the Organization/Module
    # Entitlement/RoleBinding/TenantMembership precedent above -- no legacy `approvals_changed`
    # bridge. All three Approval events collapse onto the SAME single mapping handler (every real
    # UI consumer re-reads the whole approval-request collection, never one approval row at a
    # time).
    _approval_view_invalidation_handler = build_approval_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _approval_event_type in (ApprovalRequested, ApprovalApproved, ApprovalRejected):
        platform_post_commit_bus.subscribe(
            _approval_event_type, _approval_view_invalidation_handler
        )

    _employee_list_view_invalidation_handler = build_employee_list_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _employee_event_type in (EmployeeCreated, EmployeeProfileUpdated):
        platform_post_commit_bus.subscribe(
            _employee_event_type, _employee_list_view_invalidation_handler
        )

    _department_list_view_invalidation_handler = build_department_list_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _department_event_type in (DepartmentCreated, DepartmentProfileUpdated):
        platform_post_commit_bus.subscribe(
            _department_event_type, _department_list_view_invalidation_handler
        )

    _site_list_view_invalidation_handler = build_site_list_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _site_event_type in (SiteCreated, SiteProfileUpdated, SiteEnabled, SiteDisabled):
        platform_post_commit_bus.subscribe(
            _site_event_type, _site_list_view_invalidation_handler
        )

    _party_list_view_invalidation_handler = build_party_list_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _party_event_type in (PartyCreated, PartyProfileUpdated):
        platform_post_commit_bus.subscribe(
            _party_event_type, _party_list_view_invalidation_handler
        )

    _document_list_view_invalidation_handler = build_document_list_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _document_event_type in (DocumentCreated, DocumentProfileUpdated):
        platform_post_commit_bus.subscribe(
            _document_event_type, _document_list_view_invalidation_handler
        )

    _document_structure_list_view_invalidation_handler = build_document_structure_list_view_invalidation_handler(
        platform_view_invalidation_channel
    )
    for _document_structure_event_type in (DocumentStructureCreated, DocumentStructureProfileUpdated):
        platform_post_commit_bus.subscribe(
            _document_structure_event_type, _document_structure_list_view_invalidation_handler
        )

    approval_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    approval_uow_factory = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=approval_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    approval_service = ApprovalService(
        session=session,
        approval_repo=repositories.approval_repo,
        uow_factory=approval_uow_factory,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        notification_service=notification_service,
        role_repo=repositories.role_repo,
        role_permission_repo=repositories.role_permission_repo,
        permission_repo=repositories.permission_repo,
        role_binding_repo=repositories.role_binding_repo,
        clock=SystemClock(),
    )
    overview_rollup_reader = SqlAlchemyPlatformOverviewRollupReader(session)
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
        overview_rollup_reader=overview_rollup_reader,
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

    organization_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    organization_uow_factory = SqlAlchemyOrganizationUnitOfWorkFactory(
        session_factory=organization_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    organization_service = OrganizationService(
        session=session,
        organization_repo=repositories.organization_repo,
        uow_factory=organization_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
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
    document_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    document_uow_factory = SqlAlchemyDocumentUnitOfWorkFactory(
        session_factory=document_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
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
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=document_uow_factory,
        clock=SystemClock(),
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
        uow_factory=document_uow_factory,
        clock=SystemClock(),
    )
    party_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    party_uow_factory = SqlAlchemyPartyUnitOfWorkFactory(
        session_factory=party_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    party_service = PartyService(
        session=session,
        party_repo=repositories.party_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=party_uow_factory,
        clock=SystemClock(),
    )
    site_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    site_uow_factory = SqlAlchemySiteUnitOfWorkFactory(
        session_factory=site_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    site_service = SiteService(
        session=session,
        site_repo=repositories.site_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        tenant_context_service=tenant_context_service,
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=site_uow_factory,
        clock=SystemClock(),
    )
    department_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    department_uow_factory = SqlAlchemyDepartmentUnitOfWorkFactory(
        session_factory=department_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
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
        overview_rollup_reader=overview_rollup_reader,
        uow_factory=department_uow_factory,
        clock=SystemClock(),
    )

    def _active_organization() -> Organization | None:
        return tenant_context_service.get_active_organization()

    module_entitlement_repo = SqlAlchemyModuleEntitlementRepository(
        session,
        tenant_context_service=tenant_context_service,
    )
    module_entitlement_reader = SqlAlchemyModuleEntitlementReader(session)
    configure_session_rls_context(session, user_session=user_session)
    validate_postgresql_execution_role(session)
    # P5B prerequisite (Module Entitlement Transaction Convergence): mirrors
    # `organization_uow_factory`/`provisioning_uow_factory` above -- derived from `session.bind`
    # for the same reason, and sharing the SAME composition-owned dispatcher/post-commit bus so a
    # future Module* event handler is reachable regardless of which UoW recorded it.
    module_entitlement_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    module_entitlement_uow_factory = SqlAlchemyModuleEntitlementUnitOfWorkFactory(
        session_factory=module_entitlement_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
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
        entitlement_reader=module_entitlement_reader,
        session=session,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        organization_context_provider=_active_organization,
        uow_factory=module_entitlement_uow_factory,
        clock=SystemClock(),
        view_invalidation_channel=platform_view_invalidation_channel,
    )
    logger.debug("Platform module catalog service created; bootstrapping defaults")
    module_catalog_service.bootstrap_defaults()
    logger.debug(
        "Platform module catalog defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    # P4C (Platform Runtime Organization Provisioning Transaction Convergence): mirrors
    # `organization_uow_factory`/`approval_uow_session_factory` above -- derived from
    # `session.bind` for the same reason (real engine in production, isolated test engine in
    # tests, never the shared `session` itself).
    provisioning_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    provisioning_uow_factory = SqlAlchemyPlatformProvisioningUnitOfWorkFactory(
        session_factory=provisioning_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    platform_runtime_application_service = PlatformRuntimeApplicationService(
        module_catalog_service=module_catalog_service,
        organization_service=organization_service,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        provisioning_uow_factory=provisioning_uow_factory,
    )
    runtime_execution_service = RuntimeExecutionService(
        runtime_execution_repo=SqlAlchemyRuntimeExecutionRepository(
            session,
            tenant_context_service=tenant_context_service,
        ),
        tenant_context_service=tenant_context_service,
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
            repositories.site_repo.get_for_tenant(site_id, tenant_id) is not None
        ),
    }
    role_governance_scope_exists_resolvers = {
        "organization": lambda rg_session, tenant_id, organization_id: (
            SqlAlchemyOrganizationRepository(rg_session).get_for_tenant(
                organization_id, tenant_id
            )
            is not None
        ),
        "site": lambda rg_session, tenant_id, site_id: (
            SqlAlchemySiteRepository(rg_session).get_for_tenant(site_id, tenant_id) is not None
        ),
    }
    role_governance_organization_owner_resolvers = {
        "organization": lambda _rg_session, _tenant_id, organization_id: organization_id,
        "site": lambda rg_session, tenant_id, site_id: (
            getattr(
                SqlAlchemySiteRepository(rg_session).get_for_tenant(site_id, tenant_id),
                "organization_id",
                None,
            )
        ),
    }
    role_governance_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    role_governance_uow_factory = SqlAlchemyRoleGovernanceUnitOfWorkFactory(
        session_factory=role_governance_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    role_governance_service = RoleGovernanceService(
        uow_factory=role_governance_uow_factory,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        clock=SystemClock(),
        scope_exists_resolvers=role_governance_scope_exists_resolvers,
        organization_owner_resolvers=role_governance_organization_owner_resolvers,
        allow_platform_customer_context=(
            security_configuration.tenancy_mode
            is TenancyMode.LOCAL_SINGLE_TENANT
        ),
    )
    auth_service.set_role_governance_service(role_governance_service)
    tenant_membership_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    tenant_membership_uow_factory = SqlAlchemyTenantMembershipUnitOfWorkFactory(
        session_factory=tenant_membership_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
    )
    tenant_membership_service = TenantMembershipService(
        uow_factory=tenant_membership_uow_factory,
        clock=SystemClock(),
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        notification_service=notification_service,
        # P5D-1: the SAME resolver dict `RoleGovernanceService` uses -- membership's own
        # removal cascade can revoke resource-scoped bindings too, so it needs the same
        # organization-ownership derivation, not just the tenant-wide default grant's.
        organization_owner_resolvers=role_governance_organization_owner_resolvers,
    )
    service_principal_service = ServicePrincipalService(
        session=session,
        principal_repo=repositories.service_principal_repo,
        api_key_repo=repositories.api_key_credential_repo,
        user_repo=repositories.user_repo,
        tenant_repo=repositories.tenant_repo,
        organization_repo=repositories.organization_repo,
        membership_repo=repositories.user_tenant_repo,
        audit_repo=repositories.audit_entry_repo,
        auth_service=auth_service,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
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
                ScopedRolePolicy(
                    scope_type="organization",
                    role_choices=ORGANIZATION_SCOPE_ROLE_CHOICES,
                    normalize_role=normalize_organization_scope_role,
                    resolve_permissions=resolve_organization_scope_permissions,
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
    employee_headcount_reader = SqlAlchemyEmployeeHeadcountReader(session)
    employee_uow_session_factory = sessionmaker(bind=session.bind, future=True)
    employee_uow_factory = SqlAlchemyEmployeeUnitOfWorkFactory(
        session_factory=employee_uow_session_factory,
        transactional_dispatcher=platform_transactional_dispatcher,
        post_commit_bus=platform_post_commit_bus,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        resource_repo_factory=SqlAlchemyResourceRepository,
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
        headcount_reader=employee_headcount_reader,
        uow_factory=employee_uow_factory,
        clock=SystemClock(),
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

    def _get_active_org_id() -> str:
        return tenant_context_service.get_active_organization_id() or ""

    # Constructed before the write-side calendar services below so its
    # invalidate_cache can be wired into them — this resolver is a single
    # process-lifetime instance (built once here), so a mutation that never
    # invalidates its caches leaves every later read stale until restart.
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
        shift_pattern_repo=repositories.shift_pattern_repo,
    )
    working_rule_service = WorkingRuleService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        rule_repo=repositories.calendar_working_rule_repo,
        user_session=user_session,
        on_calendar_data_changed=enterprise_calendar_resolver.invalidate_cache,
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
        on_calendar_data_changed=enterprise_calendar_resolver.invalidate_cache,
    )
    shift_pattern_service = ShiftPatternService(
        session=session,
        pattern_repo=repositories.shift_pattern_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        on_calendar_data_changed=enterprise_calendar_resolver.invalidate_cache,
    )
    calendar_assignment_service = CalendarAssignmentService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        project_assignment_repo=repositories.project_calendar_assignment_repo,
        resource_assignment_repo=repositories.resource_calendar_assignment_repo,
        user_session=user_session,
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
        platform_view_invalidation_channel=platform_view_invalidation_channel,
        platform_transactional_dispatcher=platform_transactional_dispatcher,
        platform_post_commit_bus=platform_post_commit_bus,
        platform_runtime_application_service=platform_runtime_application_service,
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
        financial_period_service=financial_period_service,
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
        service_principal_service=service_principal_service,
        global_calendar_shim=global_calendar_shim,
        runtime_security_configuration=security_configuration,
    )
    logger.debug(
        "Platform service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return bundle


__all__ = ["PlatformServiceBundle", "build_platform_service_bundle"]
