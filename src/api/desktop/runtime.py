from __future__ import annotations

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from collections.abc import Mapping
from dataclasses import dataclass

from src.api.desktop.integration import IntegrationCapabilityDesktopApi
from src.api.desktop.integration.capability_api import build_integration_capability_api
from src.api.desktop.platform import (
    PlatformAccessDesktopApi,
    PlatformApprovalDesktopApi,
    PlatformAuditDesktopApi,
    PlatformSupportDesktopApi,
)
from src.api.desktop.platform.enterprise_calendar import EnterpriseCalendarDesktopApi
from src.api.desktop.platform import (
    PlatformDocumentDesktopApi,
    PlatformDepartmentDesktopApi,
    PlatformEmployeeDesktopApi,
    PlatformPartyDesktopApi,
    PlatformRuntimeDesktopApi,
    PlatformSiteDesktopApi,
    PlatformUserDesktopApi,
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
    build_project_management_collaboration_desktop_api,
    build_project_management_dashboard_desktop_api,
    build_project_management_financials_desktop_api,
    build_project_management_portfolio_desktop_api,
    build_project_management_projects_desktop_api,
    build_project_management_register_desktop_api,
    build_project_management_resources_desktop_api,
    build_project_management_scheduling_desktop_api,
    build_project_management_tasks_desktop_api,
    build_project_management_timesheets_desktop_api,
)
from src.core.modules.inventory_procurement.api.desktop import (
    InventoryProcurementCatalogDesktopApi,
    InventoryProcurementDashboardDesktopApi,
    InventoryProcurementInventoryDesktopApi,
    InventoryProcurementPricingDesktopApi,
    InventoryProcurementProcurementDesktopApi,
    InventoryProcurementReservationsDesktopApi,
    InventoryProcurementWorkspaceDesktopApi,
    build_inventory_procurement_catalog_desktop_api,
    build_inventory_procurement_dashboard_desktop_api,
    build_inventory_procurement_inventory_desktop_api,
    build_inventory_procurement_pricing_desktop_api,
    build_inventory_procurement_procurement_desktop_api,
    build_inventory_procurement_reservations_desktop_api,
    build_inventory_procurement_workspace_desktop_api,
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
    build_maintenance_assets_desktop_api,
    build_maintenance_dashboard_desktop_api,
    build_maintenance_planner_desktop_api,
    build_maintenance_preventive_desktop_api,
    build_maintenance_reliability_desktop_api,
    build_maintenance_work_orders_desktop_api,
    build_maintenance_work_requests_desktop_api,
    build_maintenance_workspace_desktop_api,
)
from src.core.modules.maintenance import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenanceFailureCodeService,
    MaintenanceLocationService,
    MaintenancePreventiveGenerationService,
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
    MaintenanceReliabilityService,
    MaintenanceSensorService,
    MaintenanceSensorExceptionService,
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
    MaintenanceSystemService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkRequestService,
)
from src.core.modules.inventory_procurement import (
    InventoryFoundationService,
    InventoryReferenceService,
    InventoryReportingService,
    ItemCategoryService,
    ItemMasterService,
    InventoryService,
    ProcurementService,
    PurchasingService,
    ReservationService,
    StockControlService,
)
from src.application.runtime.platform_runtime import (
    PlatformRuntimeApplicationService,
    resolve_platform_runtime_application_service,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.scheduling.forecasting.schedule_change_impact_service import (
    ScheduleChangeImpactService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import FinanceService
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.resources import (
    PortfolioResourcePoolService,
    ProjectResourceService,
    ResourceAvailabilityService,
    ResourceService,
    TimesheetService,
)
from src.core.modules.project_management.application.resources.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.scheduling import (
    SchedulingEngine,
)
from src.core.modules.project_management.application.collaboration import CollaborationService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.infrastructure.reporting import ReportingService
# WorkCalendarService removed
from src.core.platform.calendar.application.enterprise_calendar_service import EnterpriseCalendarService
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.application.calendar_exception_service import CalendarExceptionService
from src.core.platform.calendar.application.recurring_event_service import RecurringEventService
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.application.calendar_assignment_service import CalendarAssignmentService
from src.core.platform.calendar.application.enterprise_calendar_resolver import EnterpriseCalendarResolver
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator
from src.core.platform.access import AccessControlService
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.approval import ApprovalService
from src.core.platform.audit import AuditService
from src.core.platform.auth.application import AuthService
from src.core.platform.documents import DocumentService
from src.core.platform.department import DepartmentService
from src.core.platform.employee import EmployeeService
from src.core.platform.site import SiteService
from src.core.platform.party import PartyService


@dataclass(frozen=True)
class DesktopApiRegistry:
    integration_capability: IntegrationCapabilityDesktopApi
    platform_runtime: PlatformRuntimeDesktopApi
    platform_calendar: None  # removed — use platform_enterprise_calendar instead
    platform_enterprise_calendar: EnterpriseCalendarDesktopApi | None
    platform_site: PlatformSiteDesktopApi
    platform_department: PlatformDepartmentDesktopApi
    platform_employee: PlatformEmployeeDesktopApi
    platform_access: PlatformAccessDesktopApi
    platform_approval: PlatformApprovalDesktopApi
    platform_audit: PlatformAuditDesktopApi
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


def _build_schedule_change_impact_service(
    task_service: TaskService | None,
    calendar,  # WorkCalendarEngine or GlobalCalendarShim (duck-typed)
) -> ScheduleChangeImpactService | None:
    if task_service is None or calendar is None:
        return None
    task_repo = getattr(task_service, "_task_repo", None)
    dependency_repo = getattr(task_service, "_dependency_repo", None)
    if task_repo is None or dependency_repo is None:
        return None
    return ScheduleChangeImpactService(
        task_repo=task_repo,
        dependency_repo=dependency_repo,
        calendar=calendar,
    )


def build_desktop_api_registry(services: Mapping[str, object]) -> DesktopApiRegistry:
    platform_runtime_application_service = resolve_platform_runtime_application_service(
        platform_runtime_application_service=services.get("platform_runtime_application_service"),
        module_runtime_service=services.get("module_runtime_service"),
        module_catalog_service=services.get("module_catalog_service"),
        organization_service=services.get("organization_service"),
    )
    if not isinstance(platform_runtime_application_service, PlatformRuntimeApplicationService):
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
    inventory_reference_service = services.get("inventory_reference_service")
    inventory_foundation_service = services.get("inventory_foundation_service")
    inventory_item_category_service = services.get("inventory_item_category_service")
    inventory_item_service = services.get("inventory_item_service")
    inventory_stock_service = services.get("inventory_stock_service")
    inventory_reservation_service = services.get("inventory_reservation_service")
    inventory_procurement_service = services.get("inventory_procurement_service")
    inventory_purchasing_service = services.get("inventory_purchasing_service")
    inventory_reporting_service = services.get("inventory_reporting_service")
    maintenance_location_service = services.get("maintenance_location_service")
    if not isinstance(maintenance_location_service, MaintenanceLocationService):
        maintenance_location_service = None
    maintenance_system_service = services.get("maintenance_system_service")
    if not isinstance(maintenance_system_service, MaintenanceSystemService):
        maintenance_system_service = None
    maintenance_asset_service = services.get("maintenance_asset_service")
    if not isinstance(maintenance_asset_service, MaintenanceAssetService):
        maintenance_asset_service = None
    maintenance_component_service = services.get("maintenance_asset_component_service")
    if not isinstance(
        maintenance_component_service,
        MaintenanceAssetComponentService,
    ):
        maintenance_component_service = None
    maintenance_work_request_service = services.get("maintenance_work_request_service")
    if not isinstance(
        maintenance_work_request_service,
        MaintenanceWorkRequestService,
    ):
        maintenance_work_request_service = None
    maintenance_work_order_service = services.get("maintenance_work_order_service")
    if not isinstance(
        maintenance_work_order_service,
        MaintenanceWorkOrderService,
    ):
        maintenance_work_order_service = None
    maintenance_material_requirement_service = services.get(
        "maintenance_work_order_material_requirement_service"
    )
    if not isinstance(
        maintenance_material_requirement_service,
        MaintenanceWorkOrderMaterialRequirementService,
    ):
        maintenance_material_requirement_service = None
    maintenance_preventive_plan_service = services.get("maintenance_preventive_plan_service")
    if not isinstance(
        maintenance_preventive_plan_service,
        MaintenancePreventivePlanService,
    ):
        maintenance_preventive_plan_service = None
    maintenance_preventive_generation_service = services.get(
        "maintenance_preventive_generation_service"
    )
    if not isinstance(
        maintenance_preventive_generation_service,
        MaintenancePreventiveGenerationService,
    ):
        maintenance_preventive_generation_service = None
    maintenance_preventive_plan_task_service = services.get(
        "maintenance_preventive_plan_task_service"
    )
    if not isinstance(
        maintenance_preventive_plan_task_service,
        MaintenancePreventivePlanTaskService,
    ):
        maintenance_preventive_plan_task_service = None
    maintenance_task_template_service = services.get("maintenance_task_template_service")
    if not isinstance(
        maintenance_task_template_service,
        MaintenanceTaskTemplateService,
    ):
        maintenance_task_template_service = None
    maintenance_task_step_template_service = services.get(
        "maintenance_task_step_template_service"
    )
    if not isinstance(
        maintenance_task_step_template_service,
        MaintenanceTaskStepTemplateService,
    ):
        maintenance_task_step_template_service = None
    maintenance_reliability_service = services.get("maintenance_reliability_service")
    if not isinstance(
        maintenance_reliability_service,
        MaintenanceReliabilityService,
    ):
        maintenance_reliability_service = None
    maintenance_sensor_service = services.get("maintenance_sensor_service")
    if not isinstance(
        maintenance_sensor_service,
        MaintenanceSensorService,
    ):
        maintenance_sensor_service = None
    maintenance_sensor_exception_service = services.get("maintenance_sensor_exception_service")
    if not isinstance(
        maintenance_sensor_exception_service,
        MaintenanceSensorExceptionService,
    ):
        maintenance_sensor_exception_service = None
    maintenance_failure_code_service = services.get("maintenance_failure_code_service")
    if not isinstance(
        maintenance_failure_code_service,
        MaintenanceFailureCodeService,
    ):
        maintenance_failure_code_service = None
    pm_project_service = (
        project_service if isinstance(project_service, ProjectService) else None
    )
    portfolio_service = services.get("portfolio_service")
    pm_portfolio_service = (
        portfolio_service if isinstance(portfolio_service, PortfolioService) else None
    )
    collaboration_service = services.get("collaboration_service")
    pm_collaboration_service = (
        collaboration_service
        if isinstance(collaboration_service, CollaborationService)
        else None
    )
    register_service = services.get("register_service")
    pm_register_service = (
        register_service if isinstance(register_service, RegisterService) else None
    )
    pm_resource_service = (
        resource_service if isinstance(resource_service, ResourceService) else None
    )
    _raw_availability_service = services.get("resource_availability_service")
    # Accept either the new EnterpriseResourceAvailabilityService or the legacy ResourceAvailabilityService.
    pm_availability_service = (
        _raw_availability_service
        if isinstance(_raw_availability_service, (ResourceAvailabilityService, EnterpriseResourceAvailabilityService))
        else None
    )
    _raw_pool_service = services.get("portfolio_resource_pool_service")
    pm_pool_service = (
        _raw_pool_service
        if isinstance(_raw_pool_service, PortfolioResourcePoolService)
        else None
    )
    project_resource_service = services.get("project_resource_service")
    pm_project_resource_service = (
        project_resource_service
        if isinstance(project_resource_service, ProjectResourceService)
        else None
    )
    timesheet_service = services.get("timesheet_service")
    pm_timesheet_service = (
        timesheet_service if isinstance(timesheet_service, TimesheetService) else None
    )
    pm_task_service = task_service if isinstance(task_service, TaskService) else None
    pm_assignment_skill_validator = services.get("assignment_skill_validator")
    if not isinstance(pm_assignment_skill_validator, AssignmentSkillValidator):
        pm_assignment_skill_validator = None
    pm_scheduling_engine = services.get("scheduling_engine")
    if not isinstance(pm_scheduling_engine, SchedulingEngine):
        pm_scheduling_engine = None
    pm_work_calendar_service = None  # WorkCalendarService removed
    # work_calendar_engine may now be a GlobalCalendarShim (duck-typed WorkCalendarEngine replacement)
    pm_work_calendar_engine = services.get("work_calendar_engine")
    if pm_work_calendar_engine is not None and not hasattr(pm_work_calendar_engine, "is_working_day"):
        pm_work_calendar_engine = None  # not calendar-like at all
    pm_dashboard_service = services.get("dashboard_service")
    if not isinstance(pm_dashboard_service, DashboardService):
        pm_dashboard_service = None
    pm_finance_service = services.get("finance_service")
    if not isinstance(pm_finance_service, FinanceService):
        pm_finance_service = None
    pm_baseline_service = (
        baseline_service if isinstance(baseline_service, BaselineService) else None
    )
    pm_reporting_service = services.get("reporting_service")
    if not isinstance(pm_reporting_service, ReportingService):
        pm_reporting_service = None
    inventory_reference_desktop_service = (
        inventory_reference_service
        if isinstance(inventory_reference_service, InventoryReferenceService)
        else None
    )
    inventory_category_desktop_service = (
        inventory_item_category_service
        if isinstance(inventory_item_category_service, ItemCategoryService)
        else None
    )
    inventory_item_desktop_service = (
        inventory_item_service
        if isinstance(inventory_item_service, ItemMasterService)
        else None
    )
    inventory_foundation_desktop_service = (
        inventory_foundation_service
        if isinstance(inventory_foundation_service, InventoryFoundationService)
        else None
    )
    inventory_inventory_desktop_service = (
        inventory_service if isinstance(inventory_service, InventoryService) else None
    )
    inventory_stock_desktop_service = (
        inventory_stock_service
        if isinstance(inventory_stock_service, StockControlService)
        else None
    )
    inventory_reservation_desktop_service = (
        inventory_reservation_service
        if isinstance(inventory_reservation_service, ReservationService)
        else None
    )
    inventory_procurement_desktop_service = (
        inventory_procurement_service
        if isinstance(inventory_procurement_service, ProcurementService)
        else None
    )
    inventory_purchasing_desktop_service = (
        inventory_purchasing_service
        if isinstance(inventory_purchasing_service, PurchasingService)
        else None
    )
    inventory_reporting_desktop_service = (
        inventory_reporting_service
        if isinstance(inventory_reporting_service, InventoryReportingService)
        else None
    )
    platform_site_api = PlatformSiteDesktopApi(site_service=site_service)
    platform_calendar_api = None  # PlatformCalendarDesktopApi removed; use EnterpriseCalendarDesktopApi
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
    access_scope_option_loaders["site"] = lambda: _load_site_scope_options(platform_site_api)
    if inventory_service is not None and hasattr(inventory_service, "list_storerooms"):
        access_scope_type_choices.append(("Storeroom", "storeroom"))
        access_scope_option_loaders["storeroom"] = lambda: [
            (f"{storeroom.storeroom_code} - {storeroom.name}", storeroom.id)
            for storeroom in inventory_service.list_storerooms()
        ]
    # Maintenance scopes — asset-level and location-level access grants
    _maint_asset_service = services.get("maintenance_asset_service")
    _maint_location_service = services.get("maintenance_location_service")
    if _maint_asset_service is not None and hasattr(_maint_asset_service, "list_assets"):
        access_scope_type_choices.append(("Asset", "maintenance"))
        access_scope_option_loaders["maintenance"] = lambda: [
            (f"{a.name} ({a.asset_code})", a.id)
            for a in _maint_asset_service.list_assets()
        ]
    elif _maint_location_service is not None and hasattr(_maint_location_service, "list_locations"):
        access_scope_type_choices.append(("Maintenance Location", "maintenance"))
        access_scope_option_loaders["maintenance"] = lambda: [
            (loc.name, loc.id)
            for loc in _maint_location_service.list_locations()
        ]
    register_desktop_api = build_project_management_register_desktop_api(
        project_service=pm_project_service,
        register_service=pm_register_service,
    )
    _module_registry = services.get("module_registry")
    if not isinstance(_module_registry, ModuleRegistry):
        from src.core.platform.integration.module_registry import ModuleRegistry as _MR
        from src.application.runtime.entitlement_runtime import ModuleRuntimeService as _MRS
        _mrt = services.get("module_runtime_service")
        _module_registry = _MR(_mrt) if isinstance(_mrt, _MRS) else None
    _integration_capability = (
        build_integration_capability_api(_module_registry) if _module_registry is not None else None
    )
    if _integration_capability is None:
        from src.core.platform.integration.module_registry import ModuleRegistry as _FallbackMR
        from src.application.runtime.entitlement_runtime import ModuleRuntimeService as _FallbackMRS
        from src.core.platform.modules import build_default_module_catalog
        _fallback_catalog = build_default_module_catalog()
        from src.application.runtime.entitlement_runtime import ModuleRuntimeService as _FMRS
        _fallback_registry = _FallbackMR(_FMRS(_fallback_catalog))
        _integration_capability = build_integration_capability_api(_fallback_registry)
    _enterprise_calendar_api: EnterpriseCalendarDesktopApi | None = None
    _ent_cal_svc = services.get("enterprise_calendar_service")
    _rule_svc = services.get("working_rule_service")
    _exc_svc = services.get("calendar_exception_service")
    _rec_svc = services.get("recurring_event_service")
    _shift_svc = services.get("shift_pattern_service")
    _assign_svc = services.get("calendar_assignment_service")
    _resolver = services.get("enterprise_calendar_resolver")
    _capacity_calc = services.get("resource_capacity_calculator")
    if (
        isinstance(_ent_cal_svc, EnterpriseCalendarService)
        and isinstance(_rule_svc, WorkingRuleService)
        and isinstance(_exc_svc, CalendarExceptionService)
        and isinstance(_rec_svc, RecurringEventService)
        and isinstance(_shift_svc, ShiftPatternService)
        and isinstance(_assign_svc, CalendarAssignmentService)
        and isinstance(_resolver, EnterpriseCalendarResolver)
    ):
        _enterprise_calendar_api = EnterpriseCalendarDesktopApi(
            calendar_service=_ent_cal_svc,
            rule_service=_rule_svc,
            exception_service=_exc_svc,
            recurring_event_service=_rec_svc,
            shift_pattern_service=_shift_svc,
            assignment_service=_assign_svc,
            resolver=_resolver,
            capacity_calculator=_capacity_calc,
        )

    return DesktopApiRegistry(
        integration_capability=_integration_capability,
        platform_runtime=PlatformRuntimeDesktopApi(
            platform_runtime_application_service=platform_runtime_application_service,
        ),
        platform_calendar=platform_calendar_api,
        platform_enterprise_calendar=_enterprise_calendar_api,
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
        project_management_dashboard=build_project_management_dashboard_desktop_api(
            project_service=pm_project_service,
            dashboard_service=pm_dashboard_service,
            baseline_service=pm_baseline_service,
            reporting_service=pm_reporting_service,
            register_service=pm_register_service,
            collaboration_service=pm_collaboration_service,
            approval_service=approval_service,
        ),
        project_management_collaboration=build_project_management_collaboration_desktop_api(
            collaboration_service=pm_collaboration_service,
        ),
        project_management_financials=build_project_management_financials_desktop_api(
            project_service=pm_project_service,
            task_service=pm_task_service,
            cost_service=(
                cost_service
                if hasattr(cost_service, "list_cost_items_for_project")
                else None
            ),
            finance_service=pm_finance_service,
            procurement_service=inventory_procurement_desktop_service,
            baseline_service=pm_baseline_service,
        ),
        project_management_portfolio=build_project_management_portfolio_desktop_api(
            project_service=pm_project_service,
            portfolio_service=pm_portfolio_service,
            pool_service=pm_pool_service,
        ),
        project_management_projects=build_project_management_projects_desktop_api(
            project_service=pm_project_service,
            project_resource_service=pm_project_resource_service,
            resource_service=pm_resource_service,
        ),
        project_management_register=register_desktop_api,
        project_management_risk=register_desktop_api,
        project_management_resources=build_project_management_resources_desktop_api(
            resource_service=pm_resource_service,
            employee_service=employee_service,
            availability_service=pm_availability_service,
            task_service=pm_task_service,
            assignment_repo=getattr(pm_task_service, "_assignment_repo", None),
            project_service=pm_project_service,
            work_calendar_engine=pm_work_calendar_engine,
        ),
        project_management_scheduling=build_project_management_scheduling_desktop_api(
            project_service=pm_project_service,
            task_service=pm_task_service,
            scheduling_engine=pm_scheduling_engine,
            platform_calendar_api=platform_calendar_api,
            work_calendar_service=pm_work_calendar_service,
            work_calendar_engine=pm_work_calendar_engine,
            baseline_service=pm_baseline_service,
            reporting_service=pm_reporting_service,
            change_impact_service=_build_schedule_change_impact_service(
                pm_task_service, pm_work_calendar_engine
            ),
        ),
        project_management_tasks=build_project_management_tasks_desktop_api(
            project_service=pm_project_service,
            task_service=pm_task_service,
            project_resource_service=pm_project_resource_service,
            resource_service=pm_resource_service,
            reservation_service=inventory_reservation_desktop_service,
            assignment_skill_validator=pm_assignment_skill_validator,
            schedule_change_impact_service=_build_schedule_change_impact_service(
                pm_task_service, pm_work_calendar_engine
            ),
        ),
        project_management_timesheets=build_project_management_timesheets_desktop_api(
            project_service=pm_project_service,
            task_service=pm_task_service,
            resource_service=pm_resource_service,
            timesheet_service=pm_timesheet_service,
        ),
        inventory_procurement_workspaces=build_inventory_procurement_workspace_desktop_api(),
        inventory_procurement_catalog=build_inventory_procurement_catalog_desktop_api(
            category_service=inventory_category_desktop_service,
            item_service=inventory_item_desktop_service,
            reference_service=inventory_reference_desktop_service,
        ),
        inventory_procurement_inventory=build_inventory_procurement_inventory_desktop_api(
            inventory_service=inventory_inventory_desktop_service,
            stock_service=inventory_stock_desktop_service,
            item_service=inventory_item_desktop_service,
            reference_service=inventory_reference_desktop_service,
            foundation_service=inventory_foundation_desktop_service,
            reservation_service=inventory_reservation_desktop_service,
            procurement_service=inventory_procurement_desktop_service,
            purchasing_service=inventory_purchasing_desktop_service,
            reporting_service=inventory_reporting_desktop_service,
            module_runtime_service=services.get("module_runtime_service"),
        ),
        inventory_procurement_reservations=build_inventory_procurement_reservations_desktop_api(
            reservation_service=inventory_reservation_desktop_service,
            item_service=inventory_item_desktop_service,
            inventory_service=inventory_inventory_desktop_service,
        ),
        inventory_procurement_procurement=build_inventory_procurement_procurement_desktop_api(
            procurement_service=inventory_procurement_desktop_service,
            purchasing_service=inventory_purchasing_desktop_service,
            reference_service=inventory_reference_desktop_service,
            inventory_service=inventory_inventory_desktop_service,
            item_service=inventory_item_desktop_service,
        ),
        inventory_procurement_dashboard=build_inventory_procurement_dashboard_desktop_api(
            item_service=inventory_item_desktop_service,
            inventory_service=inventory_inventory_desktop_service,
            stock_service=inventory_stock_desktop_service,
            reservation_service=inventory_reservation_desktop_service,
            procurement_service=inventory_procurement_desktop_service,
            purchasing_service=inventory_purchasing_desktop_service,
            reference_service=inventory_reference_desktop_service,
        ),
        inventory_procurement_pricing=build_inventory_procurement_pricing_desktop_api(
            reporting_service=inventory_reporting_desktop_service,
            reference_service=inventory_reference_desktop_service,
            inventory_service=inventory_inventory_desktop_service,
            purchasing_service=inventory_purchasing_desktop_service,
            item_service=inventory_item_desktop_service,
            user_session=services.get("user_session"),
        ),
        maintenance_workspaces=build_maintenance_workspace_desktop_api(),
        maintenance_assets=build_maintenance_assets_desktop_api(
            location_service=maintenance_location_service,
            system_service=maintenance_system_service,
            asset_service=maintenance_asset_service,
            component_service=maintenance_component_service,
            site_service=site_service,
            party_service=party_service,
        ),
        maintenance_dashboard=build_maintenance_dashboard_desktop_api(
            reliability_service=maintenance_reliability_service,
            site_service=site_service,
            asset_service=maintenance_asset_service,
            location_service=maintenance_location_service,
            system_service=maintenance_system_service,
        ),
        maintenance_planner=build_maintenance_planner_desktop_api(
            site_service=site_service,
            asset_service=maintenance_asset_service,
            system_service=maintenance_system_service,
            work_request_service=maintenance_work_request_service,
            work_order_service=maintenance_work_order_service,
            material_requirement_service=maintenance_material_requirement_service,
            preventive_plan_service=maintenance_preventive_plan_service,
            preventive_generation_service=maintenance_preventive_generation_service,
            reliability_service=maintenance_reliability_service,
            sensor_exception_service=maintenance_sensor_exception_service,
        ),
        maintenance_preventive=build_maintenance_preventive_desktop_api(
            site_service=site_service,
            asset_service=maintenance_asset_service,
            component_service=maintenance_component_service,
            system_service=maintenance_system_service,
            sensor_service=maintenance_sensor_service,
            task_template_service=maintenance_task_template_service,
            task_step_template_service=maintenance_task_step_template_service,
            preventive_plan_service=maintenance_preventive_plan_service,
            preventive_plan_task_service=maintenance_preventive_plan_task_service,
            preventive_generation_service=maintenance_preventive_generation_service,
        ),
        maintenance_reliability=build_maintenance_reliability_desktop_api(
            reliability_service=maintenance_reliability_service,
            failure_code_service=maintenance_failure_code_service,
            site_service=site_service,
            asset_service=maintenance_asset_service,
            location_service=maintenance_location_service,
            system_service=maintenance_system_service,
        ),
        maintenance_work_requests=build_maintenance_work_requests_desktop_api(
            work_request_service=maintenance_work_request_service,
            site_service=site_service,
            location_service=maintenance_location_service,
            system_service=maintenance_system_service,
            asset_service=maintenance_asset_service,
            component_service=maintenance_component_service,
        ),
        maintenance_work_orders=build_maintenance_work_orders_desktop_api(
            work_order_service=maintenance_work_order_service,
            work_request_service=maintenance_work_request_service,
            site_service=site_service,
            employee_service=employee_service,
            party_service=party_service,
            location_service=maintenance_location_service,
            system_service=maintenance_system_service,
            asset_service=maintenance_asset_service,
            component_service=maintenance_component_service,
        ),
    )


def _load_site_scope_options(platform_site_desktop_api: PlatformSiteDesktopApi) -> list[tuple[str, str]]:
    result = platform_site_desktop_api.list_sites(active_only=None)
    if not result.ok or result.data is None:
        return []
    return [
        (f"{site.site_code} - {site.name}", site.id)
        for site in result.data
    ]


__all__ = ["DesktopApiRegistry", "build_desktop_api_registry"]
