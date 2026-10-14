from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import cast

from src.core.global_overview.api.desktop.global_overview import (
    GlobalOverviewDesktopApi,
)
from src.core.modules.project_management.api.desktop import (
    ProjectManagementCollaborationDesktopApi,
    ProjectManagementDashboardDesktopApi,
    ProjectManagementFinancialsDesktopApi,
    ProjectManagementPortfolioDesktopApi,
    ProjectManagementProjectsDesktopApi,
    ProjectManagementRegisterDesktopApi,
    ProjectManagementResourcesDesktopApi,
    ProjectManagementSchedulingDesktopApi,
    ProjectManagementTasksDesktopApi,
    ProjectManagementTimesheetsDesktopApi,
)
from src.core.modules.project_management.api.desktop_runtime import (
    ProjectManagementDesktopRuntimePlatformDependencies,
    build_project_management_desktop_runtime_apis,
)
from src.core.modules.project_management.gateway.task.reservation import (
    TaskReservationGateway,
)
from src.core.platform.access import AccessControlService
from src.core.platform.api.desktop.access.access import PlatformAccessDesktopApi
from src.core.platform.api.desktop.approval.approval import PlatformApprovalDesktopApi
from src.core.platform.api.desktop.finance import FinancialPeriodDesktopApi
from src.core.platform.api.desktop.history.activity.activity import (
    PlatformActivityDesktopApi,
)
from src.core.platform.api.desktop.history.audit.audit_enterprise import (
    PlatformEnterpriseAuditDesktopApi,
)
from src.core.platform.api.desktop.integration import IntegrationCapabilityDesktopApi
from src.core.platform.api.desktop.integration.capability_api import (
    build_integration_capability_api,
)
from src.core.platform.api.desktop.master_data.department.department import (
    PlatformDepartmentDesktopApi,
)
from src.core.platform.api.desktop.master_data.documents.document import (
    PlatformDocumentDesktopApi,
)
from src.core.platform.api.desktop.master_data.employee.employee import (
    PlatformEmployeeDesktopApi,
)
from src.core.platform.api.desktop.master_data.party.party import (
    PlatformPartyDesktopApi,
)
from src.core.platform.api.desktop.master_data.site.site import PlatformSiteDesktopApi
from src.core.platform.api.desktop.notifications.notification import (
    PlatformNotificationDesktopApi,
)
from src.core.platform.api.desktop.platform_runtime.runtime import (
    PlatformRuntimeDesktopApi,
)
from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi
from src.core.platform.api.desktop.security.identity.identity import (
    PlatformIdentityDesktopApi,
)
from src.core.platform.api.desktop.support.support import PlatformSupportDesktopApi
from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.core.platform.api.desktop.time_management.calendar.platform_calendar import (
    PlatformCalendarDesktopApi,
)
from src.core.platform.application.approval import (
    ApprovalCommandHandler,
    ApprovalQueryHandler,
)
from src.core.platform.application.finance import (
    FinancialPeriodCommandHandler,
    FinancialPeriodQueryHandler,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit import EnterpriseAuditService
from src.core.platform.application.master_data.department import (
    DepartmentCommandHandler,
    DepartmentQueryHandler,
)
from src.core.platform.application.master_data.documents import (
    DocumentCommandHandler,
    DocumentQueryHandler,
    DocumentStructureCommandHandler,
)
from src.core.platform.application.master_data.employee import (
    EmployeeCommandHandler,
    EmployeeDocumentCommandHandler,
    EmployeeQueryHandler,
)
from src.core.platform.application.master_data.org import (
    OrganizationCommandHandler,
    OrganizationLifecycleCommandHandler,
    OrganizationProvisioningCommandHandler,
    OrganizationQueryHandler,
)
from src.core.platform.application.master_data.party import (
    PartyCommandHandler,
    PartyQueryHandler,
)
from src.core.platform.application.master_data.site import (
    SiteCommandHandler,
    SiteQueryHandler,
)
from src.core.platform.application.platform_runtime import (
    PlatformRuntimeQueryHandler,
)
from src.core.platform.application.security.auth import (
    AuthQueryHandler,
    AuthSessionCommandHandler,
    PasswordCommandHandler,
    UserAdministrationCommandHandler,
    UserDirectoryQueryHandler,
    UserRegistrationHandler,
)
from src.core.platform.application.security.authorization.roles.commands import (
    RoleAssignmentHandler,
)
from src.core.platform.application.security.identity import (
    ServicePrincipalCommandHandler,
    ServicePrincipalQueryHandler,
)
from src.core.platform.application.tenant.modules import (
    ModuleCatalogQueryHandler,
    ModuleEntitlementCommandHandler,
)
from src.core.platform.application.tenant.tenancy import (
    TenantAdminQueryHandler,
    TenantContextService,
    TenantInvitationCommandHandler,
    TenantLifecycleCommandHandler,
    TenantMembershipQueryHandler,
)
from src.core.platform.application.time_management.calendar.assignment.commands.calendar_assignment_commands import (
    CalendarAssignmentCommandHandler,
)
from src.core.platform.application.time_management.calendar.assignment.queries.calendar_assignment_queries import (
    CalendarAssignmentQueryHandler,
)
from src.core.platform.application.time_management.calendar.capacity.platform_calendar_resolver import (
    PlatformCalendarResolver,
)
from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
    PlatformCalendarCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.calendar_exception_commands import (
    CalendarExceptionCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.recurring_event_commands import (
    RecurringEventCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.shift_pattern_commands import (
    ShiftPatternCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.commands.working_rule_commands import (
    WorkingRuleCommandHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.calendar_exception_queries import (
    CalendarExceptionQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.recurring_event_queries import (
    RecurringEventQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.shift_pattern_queries import (
    ShiftPatternQueryHandler,
)
from src.core.platform.application.time_management.calendar.definitions.queries.working_rule_queries import (
    WorkingRuleQueryHandler,
)
from src.core.platform.application.time_management.calendar.queries.platform_calendar_queries import (
    PlatformCalendarQueryHandler,
)
from src.core.platform.domain.master_data.org import ORGANIZATION_STATUS_ACTIVE
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.shared.events.view_invalidation import ViewInvalidationChannel


@dataclass(frozen=True)
class DesktopApiRegistry:
    integration_capability: IntegrationCapabilityDesktopApi
    platform_runtime: PlatformRuntimeDesktopApi
    global_overview: GlobalOverviewDesktopApi | None
    platform_notification: PlatformNotificationDesktopApi | None

    platform_view_invalidation_channel: ViewInvalidationChannel | None
    platform_calendar: PlatformCalendarDesktopApi | None
    platform_site: PlatformSiteDesktopApi
    platform_department: PlatformDepartmentDesktopApi
    platform_employee: PlatformEmployeeDesktopApi
    platform_access: PlatformAccessDesktopApi
    platform_approval: PlatformApprovalDesktopApi
    platform_activity: PlatformActivityDesktopApi | None
    platform_enterprise_audit: PlatformEnterpriseAuditDesktopApi | None
    platform_financial_periods: FinancialPeriodDesktopApi
    platform_document: PlatformDocumentDesktopApi
    platform_party: PlatformPartyDesktopApi
    platform_support: PlatformSupportDesktopApi
    platform_tenant: PlatformTenantDesktopApi | None
    platform_user: PlatformUserDesktopApi
    platform_identity: PlatformIdentityDesktopApi
    project_management_dashboard: ProjectManagementDashboardDesktopApi
    project_management_collaboration: ProjectManagementCollaborationDesktopApi
    project_management_financials: ProjectManagementFinancialsDesktopApi
    project_management_portfolio: ProjectManagementPortfolioDesktopApi
    project_management_projects: ProjectManagementProjectsDesktopApi
    project_management_register: ProjectManagementRegisterDesktopApi
    project_management_risk: ProjectManagementRegisterDesktopApi
    project_management_resources: ProjectManagementResourcesDesktopApi
    project_management_scheduling: ProjectManagementSchedulingDesktopApi
    project_management_tasks: ProjectManagementTasksDesktopApi
    project_management_timesheets: ProjectManagementTimesheetsDesktopApi


def _require_service[T](
    services: Mapping[str, object], key: str, expected: type[T]
) -> T:
    value = services.get(key)
    if not isinstance(value, expected):
        raise RuntimeError(f"Platform capability {key!r} is not configured.")
    return value


def _optional_service[T](
    services: Mapping[str, object], key: str, expected: type[T]
) -> T | None:
    value = services.get(key)
    return value if isinstance(value, expected) else None


def build_desktop_api_registry(services: Mapping[str, object]) -> DesktopApiRegistry:
    platform_runtime_query = _require_service(
        services, "platform_runtime_query", PlatformRuntimeQueryHandler
    )
    module_entitlement_commands = services.get("module_entitlement_commands")
    if not isinstance(module_entitlement_commands, ModuleEntitlementCommandHandler):
        raise RuntimeError("Module entitlement commands are not configured.")

    site_query = _require_service(services, "site_query", SiteQueryHandler)
    department_query = _require_service(
        services, "department_query", DepartmentQueryHandler
    )
    employee_query = _require_service(services, "employee_query", EmployeeQueryHandler)
    access_service = services.get("access_service")
    if not isinstance(access_service, AccessControlService):
        raise RuntimeError("Platform access service is not configured.")
    approval_commands = _require_service(
        services, "approval_commands", ApprovalCommandHandler
    )
    approval_queries = _require_service(
        services, "approval_queries", ApprovalQueryHandler
    )
    enterprise_audit_service = services.get("enterprise_audit_service")
    financial_period_commands = _require_service(
        services, "financial_period_commands", FinancialPeriodCommandHandler
    )
    financial_period_queries = _require_service(
        services, "financial_period_queries", FinancialPeriodQueryHandler
    )
    activity_service = services.get("activity_service")
    service_principal_commands = services.get("service_principal_commands")
    if not isinstance(service_principal_commands, ServicePrincipalCommandHandler):
        raise RuntimeError("Platform service-principal commands are not configured.")
    service_principal_query = _require_service(
        services, "service_principal_query", ServicePrincipalQueryHandler
    )

    project_service = services.get("project_query")
    inventory_reservation_service = cast(
        TaskReservationGateway | None, services.get("inventory_reservation_service")
    )

    platform_site_api = PlatformSiteDesktopApi(
        site_commands=_require_service(services, "site_commands", SiteCommandHandler),
        site_query=site_query,
    )

    access_scope_type_choices: list[tuple[str, str]] = []
    access_scope_option_loaders: dict[str, Callable[[], list[tuple[str, str]]]] = {}
    access_scope_disabled_hints: dict[str, str] = {}
    organization_query = services.get("organization_query")
    if isinstance(organization_query, OrganizationQueryHandler):
        access_scope_type_choices.append(("Organization", "organization"))
        access_scope_option_loaders["organization"] = lambda: [
            (
                organization.display_name
                if organization.status == ORGANIZATION_STATUS_ACTIVE
                else f"{organization.display_name} ({organization.status})",
                organization.id,
            )
            for organization in organization_query.list_organizations(status=None)
        ]
    if project_service is not None and hasattr(project_service, "list_projects"):
        access_scope_type_choices.append(("Project", "project"))
        access_scope_option_loaders["project"] = lambda: [
            (project.name, project.id) for project in project_service.list_projects()
        ]
    access_scope_type_choices.append(("Site", "site"))
    access_scope_option_loaders["site"] = lambda: _load_site_scope_options(
        platform_site_api
    )

    module_registry = services.get("module_registry")
    if not isinstance(module_registry, ModuleRegistry):
        from src.core.platform.api.desktop_runtime.service_resolver import (
            resolve_module_catalog_service,
        )
        from src.core.platform.integration.module_registry import (
            ModuleRegistry as _ModuleRegistry,
        )

        module_catalog_service = resolve_module_catalog_service(services)
        module_registry = (
            _ModuleRegistry(module_catalog_service)
            if module_catalog_service is not None
            else None
        )
    integration_capability = (
        build_integration_capability_api(module_registry)
        if module_registry is not None
        else None
    )
    if integration_capability is None:
        from src.core.platform.application.tenant.modules import (
            build_default_module_catalog,
        )
        from src.core.platform.integration.module_registry import (
            ModuleRegistry as _FallbackModuleRegistry,
        )

        fallback_catalog = build_default_module_catalog()
        fallback_registry = _FallbackModuleRegistry(fallback_catalog)
        integration_capability = build_integration_capability_api(fallback_registry)

    platform_calendar_api: PlatformCalendarDesktopApi | None = None
    platform_calendar_commands = _optional_service(
        services, "platform_calendar_commands", PlatformCalendarCommandHandler
    )
    platform_calendar_queries = _optional_service(
        services, "platform_calendar_queries", PlatformCalendarQueryHandler
    )
    working_rule_commands = _optional_service(
        services, "working_rule_commands", WorkingRuleCommandHandler
    )
    working_rule_queries = _optional_service(
        services, "working_rule_queries", WorkingRuleQueryHandler
    )
    calendar_exception_commands = _optional_service(
        services, "calendar_exception_commands", CalendarExceptionCommandHandler
    )
    calendar_exception_queries = _optional_service(
        services, "calendar_exception_queries", CalendarExceptionQueryHandler
    )
    recurring_event_commands = _optional_service(
        services, "recurring_event_commands", RecurringEventCommandHandler
    )
    recurring_event_queries = _optional_service(
        services, "recurring_event_queries", RecurringEventQueryHandler
    )
    shift_pattern_commands = _optional_service(
        services, "shift_pattern_commands", ShiftPatternCommandHandler
    )
    shift_pattern_queries = _optional_service(
        services, "shift_pattern_queries", ShiftPatternQueryHandler
    )
    calendar_assignment_commands = _optional_service(
        services, "calendar_assignment_commands", CalendarAssignmentCommandHandler
    )
    calendar_assignment_queries = _optional_service(
        services, "calendar_assignment_queries", CalendarAssignmentQueryHandler
    )
    platform_calendar_resolver = _optional_service(
        services, "platform_calendar_resolver", PlatformCalendarResolver
    )
    resource_capacity_calculator = services.get("resource_capacity_calculator")
    platform_calendar_api = None
    if (
        platform_calendar_commands is not None
        and platform_calendar_queries is not None
        and working_rule_commands is not None
        and working_rule_queries is not None
        and calendar_exception_commands is not None
        and calendar_exception_queries is not None
        and recurring_event_commands is not None
        and recurring_event_queries is not None
        and shift_pattern_commands is not None
        and shift_pattern_queries is not None
        and calendar_assignment_commands is not None
        and calendar_assignment_queries is not None
        and platform_calendar_resolver is not None
    ):
        platform_calendar_api = PlatformCalendarDesktopApi(
            platform_calendar_commands=platform_calendar_commands,
            platform_calendar_queries=platform_calendar_queries,
            working_rule_commands=working_rule_commands,
            working_rule_queries=working_rule_queries,
            calendar_exception_commands=calendar_exception_commands,
            calendar_exception_queries=calendar_exception_queries,
            recurring_event_commands=recurring_event_commands,
            recurring_event_queries=recurring_event_queries,
            shift_pattern_commands=shift_pattern_commands,
            shift_pattern_queries=shift_pattern_queries,
            calendar_assignment_commands=calendar_assignment_commands,
            calendar_assignment_queries=calendar_assignment_queries,
            resolver=platform_calendar_resolver,
            capacity_calculator=resource_capacity_calculator,
        )

    pm_module_catalog = services.get("module_catalog_service")
    project_management_apis = build_project_management_desktop_runtime_apis(
        services=services,
        platform_dependencies=ProjectManagementDesktopRuntimePlatformDependencies(
            employee_query=employee_query,
            site_query=site_query,
            department_query=department_query,
            approval_queries=approval_queries,
            module_catalog_service=(
                pm_module_catalog
                if isinstance(pm_module_catalog, ModuleCatalogQueryHandler)
                else None
            ),
            reservation_service=inventory_reservation_service,
            platform_calendar_api=platform_calendar_api,
        ),
    )
    global_overview_api = services.get("global_overview_desktop_api")
    platform_notification_api = services.get("platform_notification_desktop_api")

    return DesktopApiRegistry(
        integration_capability=integration_capability,
        platform_view_invalidation_channel=cast(
            ViewInvalidationChannel | None,
            services.get("platform_view_invalidation_channel"),
        ),
        platform_runtime=PlatformRuntimeDesktopApi(
            platform_runtime_query=platform_runtime_query,
            module_catalog_service=_require_service(
                services, "module_catalog_service", ModuleCatalogQueryHandler
            ),
            organization_query=_require_service(
                services, "organization_query", OrganizationQueryHandler
            ),
            organization_commands=_require_service(
                services, "organization_commands", OrganizationCommandHandler
            ),
            organization_lifecycle=_require_service(
                services, "organization_lifecycle", OrganizationLifecycleCommandHandler
            ),
            organization_provisioning_commands=_require_service(
                services,
                "organization_provisioning_commands",
                OrganizationProvisioningCommandHandler,
            ),
            tenant_context_service=_require_service(
                services, "tenant_context_service", TenantContextService
            ),
            module_entitlement_commands=module_entitlement_commands,
        ),
        global_overview=(
            global_overview_api
            if isinstance(global_overview_api, GlobalOverviewDesktopApi)
            else None
        ),
        platform_notification=(
            platform_notification_api
            if isinstance(platform_notification_api, PlatformNotificationDesktopApi)
            else None
        ),
        platform_calendar=platform_calendar_api,
        platform_site=platform_site_api,
        platform_department=PlatformDepartmentDesktopApi(
            department_commands=_require_service(
                services, "department_commands", DepartmentCommandHandler
            ),
            department_query=department_query,
        ),
        platform_employee=PlatformEmployeeDesktopApi(
            employee_commands=_require_service(
                services, "employee_commands", EmployeeCommandHandler
            ),
            employee_query=employee_query,
            employee_documents=_require_service(
                services, "employee_document_commands", EmployeeDocumentCommandHandler
            ),
        ),
        platform_access=PlatformAccessDesktopApi(
            access_service=access_service,
            scope_type_choices=tuple(access_scope_type_choices),
            scope_option_loaders=access_scope_option_loaders,
            scope_disabled_hints=access_scope_disabled_hints,
        ),
        platform_approval=PlatformApprovalDesktopApi(
            approval_commands=approval_commands,
            approval_queries=approval_queries,
        ),
        platform_activity=PlatformActivityDesktopApi(activity_service=activity_service)
        if isinstance(activity_service, ActivityService)
        else None,
        platform_enterprise_audit=PlatformEnterpriseAuditDesktopApi(
            enterprise_audit_service=enterprise_audit_service
        )
        if isinstance(enterprise_audit_service, EnterpriseAuditService)
        else None,
        platform_financial_periods=FinancialPeriodDesktopApi(
            financial_period_commands=financial_period_commands,
            financial_period_queries=financial_period_queries,
        ),
        platform_document=PlatformDocumentDesktopApi(
            document_commands=_require_service(
                services, "document_commands", DocumentCommandHandler
            ),
            document_structure_commands=_require_service(
                services, "document_structure_commands", DocumentStructureCommandHandler
            ),
            document_query=_require_service(
                services, "document_query", DocumentQueryHandler
            ),
        ),
        platform_party=PlatformPartyDesktopApi(
            party_commands=_require_service(
                services, "party_commands", PartyCommandHandler
            ),
            party_query=_require_service(services, "party_query", PartyQueryHandler),
        ),
        platform_support=PlatformSupportDesktopApi(),
        platform_tenant=_build_platform_tenant_api(services),
        platform_user=PlatformUserDesktopApi(
            auth_queries=_require_service(services, "auth_queries", AuthQueryHandler),
            user_directory=_require_service(
                services, "user_directory_query", UserDirectoryQueryHandler
            ),
            registration=_require_service(
                services, "user_registration", UserRegistrationHandler
            ),
            user_administration=_require_service(
                services,
                "user_administration_commands",
                UserAdministrationCommandHandler,
            ),
            passwords=_require_service(
                services, "password_commands", PasswordCommandHandler
            ),
            session_commands=_require_service(
                services, "auth_session_commands", AuthSessionCommandHandler
            ),
            role_assignment=_require_service(
                services, "role_assignment_commands", RoleAssignmentHandler
            ),
        ),
        platform_identity=PlatformIdentityDesktopApi(
            service_principal_commands=service_principal_commands,
            service_principal_query=service_principal_query,
        ),
        **vars(project_management_apis),
    )


def _build_platform_tenant_api(
    services: Mapping[str, object],
) -> PlatformTenantDesktopApi | None:
    tenant_admin_queries = _optional_service(
        services, "tenant_admin_queries", TenantAdminQueryHandler
    )
    tenant_lifecycle_commands = _optional_service(
        services, "tenant_lifecycle_commands", TenantLifecycleCommandHandler
    )
    tenant_context_service = _optional_service(
        services, "tenant_context_service", TenantContextService
    )
    tenant_invitation_commands = _optional_service(
        services, "tenant_invitation_commands", TenantInvitationCommandHandler
    )
    tenant_membership_queries = _optional_service(
        services, "tenant_membership_queries", TenantMembershipQueryHandler
    )
    if (
        tenant_admin_queries is not None
        and tenant_lifecycle_commands is not None
        and tenant_context_service is not None
        and tenant_invitation_commands is not None
        and tenant_membership_queries is not None
    ):
        return PlatformTenantDesktopApi(
            tenant_admin_queries=tenant_admin_queries,
            tenant_lifecycle_commands=tenant_lifecycle_commands,
            tenant_context_service=tenant_context_service,
            tenant_invitation_commands=tenant_invitation_commands,
            tenant_membership_queries=tenant_membership_queries,
        )
    return None


def _load_site_scope_options(
    platform_site_desktop_api: PlatformSiteDesktopApi,
) -> list[tuple[str, str]]:
    result = platform_site_desktop_api.list_sites(active_only=None)
    if not result.ok or result.data is None:
        return []
    return [(f"{site.site_code} - {site.name}", site.id) for site in result.data]


__all__ = ["DesktopApiRegistry", "build_desktop_api_registry"]
