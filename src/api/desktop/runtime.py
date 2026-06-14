from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.api.desktop.integration import IntegrationCapabilityDesktopApi
from src.api.desktop.integration.capability_api import build_integration_capability_api
from src.api.desktop.platform import (
    PlatformAccessDesktopApi,
    PlatformActivityDesktopApi,
    PlatformApprovalDesktopApi,
    PlatformAuditDesktopApi,
    PlatformDepartmentDesktopApi,
    PlatformDocumentDesktopApi,
    PlatformEmployeeDesktopApi,
    PlatformPartyDesktopApi,
    PlatformRuntimeDesktopApi,
    PlatformSiteDesktopApi,
    PlatformSupportDesktopApi,
    PlatformUserDesktopApi,
)
from src.api.desktop.platform.audit_enterprise import PlatformEnterpriseAuditDesktopApi
from src.api.desktop.platform.enterprise_calendar import EnterpriseCalendarDesktopApi
from src.application.runtime.platform_runtime import (
    PlatformRuntimeApplicationService,
    resolve_platform_runtime_application_service,
)
from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementCatalogDesktopApi,
    InventoryProcurementDashboardDesktopApi,
    InventoryProcurementInventoryDesktopApi,
    InventoryProcurementPricingDesktopApi,
    InventoryProcurementProcurementDesktopApi,
    InventoryProcurementReservationsDesktopApi,
    InventoryProcurementWorkspaceDesktopApi,
)
from src.core.modules.inventory_procurement.api.desktop_runtime import (
    InventoryProcurementDesktopRuntimePlatformDependencies,
    build_inventory_procurement_desktop_runtime_apis,
)
from src.core.modules.maintenance.api.desktop import (
    MaintenanceAssetsDesktopApi,
    MaintenanceDashboardDesktopApi,
    MaintenancePlannerDesktopApi,
    MaintenancePreventiveDesktopApi,
    MaintenanceReliabilityDesktopApi,
    MaintenanceWorkOrdersDesktopApi,
    MaintenanceWorkRequestsDesktopApi,
    MaintenanceWorkspaceDesktopApi,
)
from src.core.modules.maintenance.api.desktop_runtime import (
    MaintenanceDesktopRuntimePlatformDependencies,
    build_maintenance_desktop_runtime_apis,
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
from src.core.platform.access import AccessControlService
from src.core.platform.approval import ApprovalService
from src.core.platform.activity.application.activity_service import ActivityService
from src.core.platform.audit import AuditService, EnterpriseAuditService
from src.core.platform.auth.application import AuthService
from src.core.platform.calendar.application.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.calendar.application.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.calendar.application.enterprise_calendar_resolver import (
    EnterpriseCalendarResolver,
)
from src.core.platform.calendar.application.enterprise_calendar_service import (
    EnterpriseCalendarService,
)
from src.core.platform.calendar.application.recurring_event_service import (
    RecurringEventService,
)
from src.core.platform.calendar.application.shift_pattern_service import (
    ShiftPatternService,
)
from src.core.platform.calendar.application.working_rule_service import (
    WorkingRuleService,
)
from src.core.platform.department import DepartmentService
from src.core.platform.documents import DocumentService
from src.core.platform.employee import EmployeeService
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.party import PartyService
from src.core.platform.site import SiteService


@dataclass(frozen=True)
class DesktopApiRegistry:
    integration_capability: IntegrationCapabilityDesktopApi
    platform_runtime: PlatformRuntimeDesktopApi
    platform_calendar: None  # removed â€” use platform_enterprise_calendar instead
    platform_enterprise_calendar: EnterpriseCalendarDesktopApi | None
    platform_site: PlatformSiteDesktopApi
    platform_department: PlatformDepartmentDesktopApi
    platform_employee: PlatformEmployeeDesktopApi
    platform_access: PlatformAccessDesktopApi
    platform_approval: PlatformApprovalDesktopApi
    platform_activity: PlatformActivityDesktopApi | None
    platform_audit: PlatformAuditDesktopApi
    platform_enterprise_audit: PlatformEnterpriseAuditDesktopApi | None
    platform_document: PlatformDocumentDesktopApi
    platform_party: PlatformPartyDesktopApi
    platform_support: PlatformSupportDesktopApi
    platform_user: PlatformUserDesktopApi
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
    inventory_procurement_workspaces: InventoryProcurementWorkspaceDesktopApi
    inventory_procurement_catalog: InventoryProcurementCatalogDesktopApi
    inventory_procurement_inventory: InventoryProcurementInventoryDesktopApi
    inventory_procurement_reservations: InventoryProcurementReservationsDesktopApi
    inventory_procurement_procurement: InventoryProcurementProcurementDesktopApi
    inventory_procurement_dashboard: InventoryProcurementDashboardDesktopApi
    inventory_procurement_pricing: InventoryProcurementPricingDesktopApi
    maintenance_workspaces: MaintenanceWorkspaceDesktopApi
    maintenance_assets: MaintenanceAssetsDesktopApi
    maintenance_dashboard: MaintenanceDashboardDesktopApi
    maintenance_planner: MaintenancePlannerDesktopApi
    maintenance_preventive: MaintenancePreventiveDesktopApi
    maintenance_reliability: MaintenanceReliabilityDesktopApi
    maintenance_work_requests: MaintenanceWorkRequestsDesktopApi
    maintenance_work_orders: MaintenanceWorkOrdersDesktopApi


def build_desktop_api_registry(services: Mapping[str, object]) -> DesktopApiRegistry:
    platform_runtime_application_service = resolve_platform_runtime_application_service(
        platform_runtime_application_service=services.get(
            "platform_runtime_application_service"
        ),
        module_runtime_service=services.get("module_runtime_service"),
        module_catalog_service=services.get("module_catalog_service"),
        organization_service=services.get("organization_service"),
        tenant_context_service=services.get("tenant_context_service"),
        user_session=services.get("user_session"),
    )
    if not isinstance(
        platform_runtime_application_service,
        PlatformRuntimeApplicationService,
    ):
        raise RuntimeError("Platform runtime application service is not configured.")

    site_service = services.get("site_service")
    if not isinstance(site_service, SiteService):
        raise RuntimeError("Platform site service is not configured.")
    department_service = services.get("department_service")
    if not isinstance(department_service, DepartmentService):
        raise RuntimeError("Platform department service is not configured.")
    employee_service = services.get("employee_service")
    if not isinstance(employee_service, EmployeeService):
        raise RuntimeError("Platform employee service is not configured.")
    access_service = services.get("access_service")
    if not isinstance(access_service, AccessControlService):
        raise RuntimeError("Platform access service is not configured.")
    approval_service = services.get("approval_service")
    if not isinstance(approval_service, ApprovalService):
        raise RuntimeError("Platform approval service is not configured.")
    audit_service = services.get("audit_service")
    if not isinstance(audit_service, AuditService):
        raise RuntimeError("Platform audit service is not configured.")
    enterprise_audit_service = services.get("enterprise_audit_service")
    activity_service = services.get("activity_service")
    document_service = services.get("document_service")
    if not isinstance(document_service, DocumentService):
        raise RuntimeError("Platform document service is not configured.")
    party_service = services.get("party_service")
    if not isinstance(party_service, PartyService):
        raise RuntimeError("Platform party service is not configured.")
    auth_service = services.get("auth_service")
    if not isinstance(auth_service, AuthService):
        raise RuntimeError("Platform auth service is not configured.")

    project_service = services.get("project_service")
    task_service = services.get("task_service")
    resource_service = services.get("resource_service")
    cost_service = services.get("cost_service")
    baseline_service = services.get("baseline_service")
    inventory_service = services.get("inventory_service")
    inventory_reservation_service = services.get("inventory_reservation_service")
    inventory_procurement_service = services.get("inventory_procurement_service")
    inventory_purchasing_service = services.get("inventory_purchasing_service")

    platform_site_api = PlatformSiteDesktopApi(site_service=site_service)
    platform_calendar_api = (
        None
    )  # PlatformCalendarDesktopApi removed; use EnterpriseCalendarDesktopApi

    access_scope_type_choices: list[tuple[str, str]] = []
    access_scope_option_loaders: dict[str, object] = {}
    access_scope_disabled_hints: dict[str, str] = {}
    if project_service is not None and hasattr(project_service, "list_projects"):
        access_scope_type_choices.append(("Project", "project"))
        access_scope_option_loaders["project"] = lambda: [
            (project.name, project.id)
            for project in project_service.list_projects()
        ]
    access_scope_type_choices.append(("Site", "site"))
    access_scope_option_loaders["site"] = lambda: _load_site_scope_options(
        platform_site_api
    )
    if inventory_service is not None and hasattr(
        inventory_service,
        "list_storerooms",
    ):
        access_scope_type_choices.append(("Storeroom", "storeroom"))
        access_scope_option_loaders["storeroom"] = lambda: [
            (f"{storeroom.storeroom_code} - {storeroom.name}", storeroom.id)
            for storeroom in inventory_service.list_storerooms()
        ]

    maintenance_asset_service = services.get("maintenance_asset_service")
    maintenance_location_service = services.get("maintenance_location_service")
    if maintenance_asset_service is not None and hasattr(
        maintenance_asset_service,
        "list_assets",
    ):
        access_scope_type_choices.append(("Asset", "maintenance"))
        access_scope_option_loaders["maintenance"] = lambda: [
            (f"{asset.name} ({asset.asset_code})", asset.id)
            for asset in maintenance_asset_service.list_assets()
        ]
    elif maintenance_location_service is not None and hasattr(
        maintenance_location_service,
        "list_locations",
    ):
        access_scope_type_choices.append(("Maintenance Location", "maintenance"))
        access_scope_option_loaders["maintenance"] = lambda: [
            (location.name, location.id)
            for location in maintenance_location_service.list_locations()
        ]

    module_registry = services.get("module_registry")
    if not isinstance(module_registry, ModuleRegistry):
        from src.application.runtime.entitlement_runtime import (
            ModuleRuntimeService as _ModuleRuntimeService,
        )
        from src.core.platform.integration.module_registry import (
            ModuleRegistry as _ModuleRegistry,
        )

        module_runtime_service = services.get("module_runtime_service")
        module_registry = (
            _ModuleRegistry(module_runtime_service)
            if isinstance(module_runtime_service, _ModuleRuntimeService)
            else None
        )
    integration_capability = (
        build_integration_capability_api(module_registry)
        if module_registry is not None
        else None
    )
    if integration_capability is None:
        from src.application.runtime.entitlement_runtime import (
            ModuleRuntimeService as _FallbackModuleRuntimeService,
        )
        from src.core.platform.integration.module_registry import (
            ModuleRegistry as _FallbackModuleRegistry,
        )
        from src.core.platform.modules import build_default_module_catalog

        fallback_catalog = build_default_module_catalog()
        fallback_registry = _FallbackModuleRegistry(
            _FallbackModuleRuntimeService(fallback_catalog)
        )
        integration_capability = build_integration_capability_api(fallback_registry)

    enterprise_calendar_api: EnterpriseCalendarDesktopApi | None = None
    enterprise_calendar_service = services.get("enterprise_calendar_service")
    working_rule_service = services.get("working_rule_service")
    calendar_exception_service = services.get("calendar_exception_service")
    recurring_event_service = services.get("recurring_event_service")
    shift_pattern_service = services.get("shift_pattern_service")
    calendar_assignment_service = services.get("calendar_assignment_service")
    enterprise_calendar_resolver = services.get("enterprise_calendar_resolver")
    resource_capacity_calculator = services.get("resource_capacity_calculator")
    if (
        isinstance(enterprise_calendar_service, EnterpriseCalendarService)
        and isinstance(working_rule_service, WorkingRuleService)
        and isinstance(calendar_exception_service, CalendarExceptionService)
        and isinstance(recurring_event_service, RecurringEventService)
        and isinstance(shift_pattern_service, ShiftPatternService)
        and isinstance(calendar_assignment_service, CalendarAssignmentService)
        and isinstance(enterprise_calendar_resolver, EnterpriseCalendarResolver)
    ):
        enterprise_calendar_api = EnterpriseCalendarDesktopApi(
            calendar_service=enterprise_calendar_service,
            rule_service=working_rule_service,
            exception_service=calendar_exception_service,
            recurring_event_service=recurring_event_service,
            shift_pattern_service=shift_pattern_service,
            assignment_service=calendar_assignment_service,
            resolver=enterprise_calendar_resolver,
            capacity_calculator=resource_capacity_calculator,
        )

    project_management_apis = build_project_management_desktop_runtime_apis(
        services=services,
        platform_dependencies=ProjectManagementDesktopRuntimePlatformDependencies(
            employee_service=employee_service,
            site_service=site_service,
            approval_service=approval_service,
            procurement_service=inventory_procurement_service,
            reservation_service=inventory_reservation_service,
        ),
    )
    inventory_procurement_apis = build_inventory_procurement_desktop_runtime_apis(
        services=services,
        platform_dependencies=InventoryProcurementDesktopRuntimePlatformDependencies(
            module_runtime_service=services.get("module_runtime_service"),
            user_session=services.get("user_session"),
        ),
    )
    maintenance_apis = build_maintenance_desktop_runtime_apis(
        services=services,
        platform_dependencies=MaintenanceDesktopRuntimePlatformDependencies(
            site_service=site_service,
            party_service=party_service,
            employee_service=employee_service,
        ),
    )

    return DesktopApiRegistry(
        integration_capability=integration_capability,
        platform_runtime=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=platform_runtime_application_service,
        ),
        platform_calendar=platform_calendar_api,
        platform_enterprise_calendar=enterprise_calendar_api,
        platform_site=platform_site_api,
        platform_department=PlatformDepartmentDesktopApi(
            department_service=department_service,
        ),
        platform_employee=PlatformEmployeeDesktopApi(
            employee_service=employee_service,
        ),
        platform_access=PlatformAccessDesktopApi(
            access_service=access_service,
            scope_type_choices=tuple(access_scope_type_choices),
            scope_option_loaders=access_scope_option_loaders,
            scope_disabled_hints=access_scope_disabled_hints,
        ),
        platform_approval=PlatformApprovalDesktopApi(
            approval_service=approval_service,
        ),
        platform_activity=PlatformActivityDesktopApi(activity_service=activity_service) if isinstance(activity_service, ActivityService) else None,
        platform_enterprise_audit=PlatformEnterpriseAuditDesktopApi(enterprise_audit_service=enterprise_audit_service) if isinstance(enterprise_audit_service, EnterpriseAuditService) else None,
        platform_audit=PlatformAuditDesktopApi(
            audit_service=audit_service,
            project_service=project_service,
            task_service=task_service,
            resource_service=resource_service,
            cost_service=cost_service,
            baseline_service=baseline_service,
            reservation_service=inventory_reservation_service,
            procurement_service=inventory_procurement_service,
            purchasing_service=inventory_purchasing_service,
        ),
        platform_document=PlatformDocumentDesktopApi(
            document_service=document_service,
        ),
        platform_party=PlatformPartyDesktopApi(
            party_service=party_service,
        ),
        platform_support=PlatformSupportDesktopApi(),
        platform_user=PlatformUserDesktopApi(
            auth_service=auth_service,
        ),
        **vars(project_management_apis),
        **vars(inventory_procurement_apis),
        **vars(maintenance_apis),
    )


def _load_site_scope_options(
    platform_site_desktop_api: PlatformSiteDesktopApi,
) -> list[tuple[str, str]]:
    result = platform_site_desktop_api.list_sites(active_only=None)
    if not result.ok or result.data is None:
        return []
    return [
        (f"{site.site_code} - {site.name}", site.id)
        for site in result.data
    ]


__all__ = ["DesktopApiRegistry", "build_desktop_api_registry"]
