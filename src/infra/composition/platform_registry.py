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
from src.core.platform.approval import ApprovalService
from src.core.platform.audit import AuditService
from src.core.platform.auth import AuthService
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.documents import DocumentIntegrationService, DocumentService
from src.core.platform.data_exchange import MasterDataExchangeService
from src.core.platform.department import DepartmentService
from src.core.platform.employee import EmployeeService
from src.core.platform.org import OrganizationRepository, OrganizationService
from src.core.platform.site import SiteRepository, SiteService
from src.core.platform.site.access_policy import (
    SITE_SCOPE_ROLE_CHOICES,
    normalize_site_scope_role,
    resolve_site_scope_permissions,
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


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PlatformServiceBundle:
    session: Session
    user_session: UserSessionContext
    organization_repo: OrganizationRepository
    site_repo: SiteRepository
    party_repo: PartyRepository
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_runtime_service: ModuleRuntimeService
    module_catalog_service: ModuleCatalogService
    auth_service: AuthService
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
    audit_service: AuditService
    approval_service: ApprovalService
    enterprise_calendar_service: EnterpriseCalendarService
    working_rule_service: WorkingRuleService
    calendar_exception_service: CalendarExceptionService
    recurring_event_service: RecurringEventService
    shift_pattern_service: ShiftPatternService
    calendar_assignment_service: CalendarAssignmentService
    enterprise_calendar_resolver: EnterpriseCalendarResolver
    working_time_calculator: WorkingTimeCalculator
    global_calendar_shim: GlobalCalendarShim


def build_platform_service_bundle(
    session: Session,
    repositories: RepositoryBundle,
) -> PlatformServiceBundle:
    started = perf_counter()
    logger.info("Platform service bundle build begin")
    user_session = UserSessionContext()
    audit_service = AuditService(
        session=session,
        audit_repo=repositories.audit_repo,
        user_session=user_session,
    )
    approval_service = ApprovalService(
        session=session,
        approval_repo=repositories.approval_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    auth_service = AuthService(
        session=session,
        user_repo=repositories.user_repo,
        role_repo=repositories.role_repo,
        permission_repo=repositories.permission_repo,
        user_role_repo=repositories.user_role_repo,
        role_permission_repo=repositories.role_permission_repo,
        auth_session_repo=repositories.auth_session_repo,
        scoped_access_repo=repositories.scoped_access_repo,
        project_membership_repo=repositories.project_membership_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    user_session.set_validator(auth_service.validate_session_principal)
    logger.info("Platform auth service created; bootstrapping defaults")
    auth_service.bootstrap_defaults()
    logger.info(
        "Platform auth defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )

    organization_service = OrganizationService(
        session=session,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    logger.info("Platform organization service created; bootstrapping defaults")
    organization_service.bootstrap_defaults()
    logger.info(
        "Platform organization defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )

    document_service = DocumentService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    document_integration_service = DocumentIntegrationService(
        session=session,
        document_repo=repositories.document_repo,
        link_repo=repositories.document_link_repo,
        structure_repo=repositories.document_structure_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    party_service = PartyService(
        session=session,
        party_repo=repositories.party_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    site_service = SiteService(
        session=session,
        site_repo=repositories.site_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
    )
    department_service = DepartmentService(
        session=session,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        employee_repo=repositories.employee_repo,
        user_session=user_session,
        audit_service=audit_service,
    )

    def _active_organization():
        return repositories.organization_repo.get_active()

    def _active_organization_id() -> str | None:
        organization = _active_organization()
        return organization.id if organization is not None else None

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
        audit_service=audit_service,
        organization_context_provider=_active_organization,
    )
    logger.info("Platform module catalog service created; bootstrapping defaults")
    module_catalog_service.bootstrap_defaults()
    logger.info(
        "Platform module catalog defaults bootstrapped duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    module_runtime_service = ModuleRuntimeService(module_catalog_service)
    platform_runtime_application_service = PlatformRuntimeApplicationService(
        module_runtime_service=module_runtime_service,
        organization_service=organization_service,
    )
    runtime_execution_service = RuntimeExecutionService(
        runtime_execution_repo=SqlAlchemyRuntimeExecutionRepository(session),
        user_session=user_session,
    )
    access_service = AccessControlService(
        session=session,
        membership_repo=repositories.project_membership_repo,
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
        scoped_access_repo=repositories.scoped_access_repo,
        scope_exists_resolvers={
            "site": lambda site_id: repositories.site_repo.get(site_id) is not None,
        },
        user_session=user_session,
        audit_service=audit_service,
    )
    employee_service = EmployeeService(
        session=session,
        employee_repo=repositories.employee_repo,
        resource_repo=repositories.resource_repo,
        site_repo=repositories.site_repo,
        department_repo=repositories.department_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        audit_service=audit_service,
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
        audit_service=audit_service,
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
    )
    calendar_assignment_service = CalendarAssignmentService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        project_assignment_repo=repositories.project_calendar_assignment_repo,
        resource_assignment_repo=repositories.resource_calendar_assignment_repo,
        user_session=user_session,
    )

    def _get_active_org_id():
        org = repositories.organization_repo.get_active()
        return org.id if org else ""

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
        org = repositories.organization_repo.get_active()
        if org:
            logger.info("Ensuring enterprise global calendar organization_id=%s", org.id)
            enterprise_calendar_service.ensure_global_calendar(org.id)
            logger.info("Enterprise global calendar ensured organization_id=%s", org.id)
    except Exception:
        logger.exception("Enterprise global calendar bootstrap failed; continuing startup")

    bundle = PlatformServiceBundle(
        session=session,
        user_session=user_session,
        organization_repo=repositories.organization_repo,
        site_repo=repositories.site_repo,
        party_repo=repositories.party_repo,
        platform_runtime_application_service=platform_runtime_application_service,
        module_runtime_service=module_runtime_service,
        module_catalog_service=module_catalog_service,
        auth_service=auth_service,
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
        audit_service=audit_service,
        approval_service=approval_service,
        enterprise_calendar_service=enterprise_calendar_service,
        working_rule_service=working_rule_service,
        calendar_exception_service=calendar_exception_service,
        recurring_event_service=recurring_event_service,
        shift_pattern_service=shift_pattern_service,
        calendar_assignment_service=calendar_assignment_service,
        enterprise_calendar_resolver=enterprise_calendar_resolver,
        working_time_calculator=working_time_calculator,
        global_calendar_shim=global_calendar_shim,
    )
    logger.info(
        "Platform service bundle build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return bundle


__all__ = ["PlatformServiceBundle", "build_platform_service_bundle"]
