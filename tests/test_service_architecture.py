from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.platform.common.service_base import ServiceBase as LegacyServiceBase
from core.platform.access import AccessControlService
from core.platform.approval import ApprovalService
from core.platform.approval.service import ApprovalService as LegacyApprovalService
from core.platform.auth import AuthService
from core.platform.auth.service import AuthService as LegacyAuthService
from core.platform.audit import AuditService
from core.platform.audit.service import AuditService as LegacyAuditService
from core.platform.data_exchange import MasterDataExchangeService
from core.platform.documents import DocumentService
from core.platform.org import DepartmentService, EmployeeService, OrganizationService, SiteService
from core.platform.party import PartyService
from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.core.platform.time.application import TimeService
from core.modules.inventory_procurement import (
    InventoryDataExchangeService,
    MaintenanceMaterialService,
    InventoryReferenceService,
    InventoryReportingService,
    InventoryService,
    ItemCategoryService,
    ItemMasterService,
    ProcurementService,
    PurchasingService,
    ReservationService,
    StockControlService,
)
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenanceAssetComponentService,
    MaintenanceDocumentService,
    MaintenanceDowntimeEventService,
    MaintenanceFailureCodeService,
    MaintenanceIntegrationSourceService,
    MaintenanceLaborService,
    MaintenanceLocationService,
    MaintenancePreventiveGenerationService,
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
    MaintenanceReliabilityService,
    MaintenanceReportingService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceRuntimeContractCatalogService,
    MaintenanceSensorExceptionService,
    MaintenanceSensorReadingService,
    MaintenanceSensorService,
    MaintenanceSensorSourceMappingService,
    MaintenanceSystemService,
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
    MaintenanceWorkOrderService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkOrderTaskStepService,
    MaintenanceWorkRequestService,
)
from core.modules.project_management.services.baseline import BaselineService
from core.modules.project_management.services.baseline.service import BaselineService as LegacyBaselineService
from core.modules.project_management.services.calendar import CalendarService
from core.modules.project_management.services.collaboration import CollaborationService
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.dashboard import DashboardService
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.finance.service import FinanceService as LegacyFinanceService
from core.modules.project_management.services.portfolio import PortfolioService
from core.modules.project_management.services.project import ProjectResourceService, ProjectService
from core.modules.project_management.services.register import RegisterService
from core.modules.project_management.services.register.service import RegisterService as LegacyRegisterService
from core.modules.project_management.services.calendar.service import CalendarService as LegacyCalendarService
from core.modules.project_management.services.project.resource_service import ProjectResourceService as LegacyProjectResourceService
from core.modules.project_management.services.project.service import ProjectService as LegacyProjectService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.reporting.service import ReportingService as LegacyReportingService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.resource.service import ResourceService as LegacyResourceService
from core.modules.project_management.services.scheduling import CPMTaskInfo, SchedulingEngine
from core.modules.project_management.services.scheduling.engine import CPMTaskInfo as LegacyCPMTaskInfo
from core.modules.project_management.services.scheduling.engine import SchedulingEngine as LegacySchedulingEngine
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.task.service import TaskService as LegacyTaskService
from core.modules.project_management.services.timesheet import TimesheetService
from core.modules.project_management.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from core.modules.project_management.services.work_calendar.engine import WorkCalendarEngine as LegacyWorkCalendarEngine
from core.modules.project_management.services.work_calendar.service import WorkCalendarService as LegacyWorkCalendarService
from src.infra.composition.app_container import ServiceGraph, build_service_graph
from pathlib import Path


def test_service_graph_builder_wires_all_services(session):
    graph = build_service_graph(session)

    assert isinstance(graph, ServiceGraph)
    assert isinstance(graph.platform_runtime_application_service, PlatformRuntimeApplicationService)
    assert isinstance(graph.module_runtime_service, ModuleRuntimeService)
    assert isinstance(graph.time_service, TimeService)
    assert isinstance(graph.approval_service, ApprovalService)
    assert isinstance(graph.auth_service, AuthService)
    assert isinstance(graph.organization_service, OrganizationService)
    assert isinstance(graph.document_service, DocumentService)
    assert isinstance(graph.party_service, PartyService)
    assert isinstance(graph.department_service, DepartmentService)
    assert isinstance(graph.site_service, SiteService)
    assert isinstance(graph.employee_service, EmployeeService)
    assert isinstance(graph.master_data_exchange_service, MasterDataExchangeService)
    assert isinstance(graph.inventory_reference_service, InventoryReferenceService)
    assert isinstance(graph.inventory_data_exchange_service, InventoryDataExchangeService)
    assert isinstance(graph.inventory_reporting_service, InventoryReportingService)
    assert isinstance(graph.inventory_item_category_service, ItemCategoryService)
    assert isinstance(graph.inventory_item_service, ItemMasterService)
    assert isinstance(graph.inventory_maintenance_material_service, MaintenanceMaterialService)
    assert isinstance(graph.inventory_service, InventoryService)
    assert isinstance(graph.inventory_stock_service, StockControlService)
    assert isinstance(graph.inventory_reservation_service, ReservationService)
    assert isinstance(graph.inventory_procurement_service, ProcurementService)
    assert isinstance(graph.inventory_purchasing_service, PurchasingService)
    assert isinstance(graph.maintenance_runtime_contract_catalog_service, MaintenanceRuntimeContractCatalogService)
    assert isinstance(graph.maintenance_asset_service, MaintenanceAssetService)
    assert isinstance(graph.maintenance_asset_component_service, MaintenanceAssetComponentService)
    assert isinstance(graph.maintenance_document_service, MaintenanceDocumentService)
    assert isinstance(graph.maintenance_downtime_event_service, MaintenanceDowntimeEventService)
    assert isinstance(graph.maintenance_failure_code_service, MaintenanceFailureCodeService)
    assert isinstance(graph.maintenance_integration_source_service, MaintenanceIntegrationSourceService)
    assert isinstance(graph.maintenance_labor_service, MaintenanceLaborService)
    assert isinstance(graph.maintenance_location_service, MaintenanceLocationService)
    assert isinstance(graph.maintenance_preventive_generation_service, MaintenancePreventiveGenerationService)
    assert isinstance(graph.maintenance_preventive_plan_service, MaintenancePreventivePlanService)
    assert isinstance(graph.maintenance_preventive_plan_task_service, MaintenancePreventivePlanTaskService)
    assert isinstance(graph.maintenance_reliability_service, MaintenanceReliabilityService)
    assert isinstance(graph.maintenance_reporting_service, MaintenanceReportingService)
    assert isinstance(graph.maintenance_sensor_exception_service, MaintenanceSensorExceptionService)
    assert isinstance(graph.maintenance_sensor_service, MaintenanceSensorService)
    assert isinstance(graph.maintenance_sensor_reading_service, MaintenanceSensorReadingService)
    assert isinstance(graph.maintenance_sensor_source_mapping_service, MaintenanceSensorSourceMappingService)
    assert isinstance(graph.maintenance_system_service, MaintenanceSystemService)
    assert isinstance(graph.maintenance_task_step_template_service, MaintenanceTaskStepTemplateService)
    assert isinstance(graph.maintenance_task_template_service, MaintenanceTaskTemplateService)
    assert isinstance(graph.maintenance_work_request_service, MaintenanceWorkRequestService)
    assert isinstance(graph.maintenance_work_order_service, MaintenanceWorkOrderService)
    assert isinstance(graph.maintenance_work_order_material_requirement_service, MaintenanceWorkOrderMaterialRequirementService)
    assert isinstance(graph.maintenance_work_order_task_service, MaintenanceWorkOrderTaskService)
    assert isinstance(graph.maintenance_work_order_task_step_service, MaintenanceWorkOrderTaskStepService)
    assert isinstance(graph.access_service, AccessControlService)
    assert isinstance(graph.audit_service, AuditService)
    assert isinstance(graph.collaboration_service, CollaborationService)
    assert isinstance(graph.project_service, ProjectService)
    assert isinstance(graph.task_service, TaskService)
    assert isinstance(graph.timesheet_service, TimesheetService)
    assert isinstance(graph.resource_service, ResourceService)
    assert isinstance(graph.calendar_service, CalendarService)
    assert isinstance(graph.cost_service, CostService)
    assert isinstance(graph.finance_service, FinanceService)
    assert isinstance(graph.work_calendar_engine, WorkCalendarEngine)
    assert isinstance(graph.work_calendar_service, WorkCalendarService)
    assert isinstance(graph.scheduling_engine, SchedulingEngine)
    assert isinstance(graph.reporting_service, ReportingService)
    assert isinstance(graph.baseline_service, BaselineService)
    assert isinstance(graph.dashboard_service, DashboardService)
    assert isinstance(graph.portfolio_service, PortfolioService)
    assert isinstance(graph.register_service, RegisterService)
    assert isinstance(graph.project_resource_service, ProjectResourceService)

    as_dict = graph.as_dict()
    assert as_dict["approval_service"] is graph.approval_service
    assert as_dict["auth_service"] is graph.auth_service
    assert as_dict["platform_runtime_application_service"] is graph.platform_runtime_application_service
    assert as_dict["organization_service"] is graph.organization_service
    assert as_dict["document_service"] is graph.document_service
    assert as_dict["party_service"] is graph.party_service
    assert as_dict["department_service"] is graph.department_service
    assert as_dict["site_service"] is graph.site_service
    assert as_dict["employee_service"] is graph.employee_service
    assert as_dict["master_data_exchange_service"] is graph.master_data_exchange_service
    assert as_dict["inventory_reference_service"] is graph.inventory_reference_service
    assert as_dict["inventory_data_exchange_service"] is graph.inventory_data_exchange_service
    assert as_dict["inventory_reporting_service"] is graph.inventory_reporting_service
    assert as_dict["inventory_item_category_service"] is graph.inventory_item_category_service
    assert as_dict["inventory_item_service"] is graph.inventory_item_service
    assert as_dict["inventory_maintenance_material_service"] is graph.inventory_maintenance_material_service
    assert as_dict["inventory_service"] is graph.inventory_service
    assert as_dict["inventory_stock_service"] is graph.inventory_stock_service
    assert as_dict["inventory_reservation_service"] is graph.inventory_reservation_service
    assert as_dict["inventory_procurement_service"] is graph.inventory_procurement_service
    assert as_dict["inventory_purchasing_service"] is graph.inventory_purchasing_service
    assert (
        as_dict["maintenance_runtime_contract_catalog_service"]
        is graph.maintenance_runtime_contract_catalog_service
    )
    assert as_dict["maintenance_asset_service"] is graph.maintenance_asset_service
    assert as_dict["maintenance_asset_component_service"] is graph.maintenance_asset_component_service
    assert as_dict["maintenance_document_service"] is graph.maintenance_document_service
    assert as_dict["maintenance_downtime_event_service"] is graph.maintenance_downtime_event_service
    assert as_dict["maintenance_failure_code_service"] is graph.maintenance_failure_code_service
    assert as_dict["maintenance_integration_source_service"] is graph.maintenance_integration_source_service
    assert as_dict["maintenance_labor_service"] is graph.maintenance_labor_service
    assert as_dict["maintenance_location_service"] is graph.maintenance_location_service
    assert as_dict["maintenance_preventive_generation_service"] is graph.maintenance_preventive_generation_service
    assert as_dict["maintenance_preventive_plan_service"] is graph.maintenance_preventive_plan_service
    assert as_dict["maintenance_preventive_plan_task_service"] is graph.maintenance_preventive_plan_task_service
    assert as_dict["maintenance_reliability_service"] is graph.maintenance_reliability_service
    assert as_dict["maintenance_reporting_service"] is graph.maintenance_reporting_service
    assert as_dict["maintenance_sensor_exception_service"] is graph.maintenance_sensor_exception_service
    assert as_dict["maintenance_sensor_service"] is graph.maintenance_sensor_service
    assert as_dict["maintenance_sensor_reading_service"] is graph.maintenance_sensor_reading_service
    assert as_dict["maintenance_sensor_source_mapping_service"] is graph.maintenance_sensor_source_mapping_service
    assert as_dict["maintenance_system_service"] is graph.maintenance_system_service
    assert as_dict["maintenance_task_step_template_service"] is graph.maintenance_task_step_template_service
    assert as_dict["maintenance_task_template_service"] is graph.maintenance_task_template_service
    assert as_dict["maintenance_work_request_service"] is graph.maintenance_work_request_service
    assert as_dict["maintenance_work_order_service"] is graph.maintenance_work_order_service
    assert (
        as_dict["maintenance_work_order_material_requirement_service"]
        is graph.maintenance_work_order_material_requirement_service
    )
    assert as_dict["maintenance_work_order_task_service"] is graph.maintenance_work_order_task_service
    assert as_dict["maintenance_work_order_task_step_service"] is graph.maintenance_work_order_task_step_service
    assert as_dict["module_runtime_service"] is graph.module_runtime_service
    assert as_dict["time_service"] is graph.time_service
    assert as_dict["access_service"] is graph.access_service
    assert as_dict["audit_service"] is graph.audit_service
    assert as_dict["collaboration_service"] is graph.collaboration_service
    assert as_dict["dashboard_service"] is graph.dashboard_service
    assert as_dict["finance_service"] is graph.finance_service
    assert as_dict["portfolio_service"] is graph.portfolio_service
    assert as_dict["register_service"] is graph.register_service
    assert as_dict["project_resource_service"] is graph.project_resource_service
    assert as_dict["timesheet_service"] is graph.timesheet_service
    assert as_dict["session"] is session
    assert graph.time_service is graph.timesheet_service


def test_legacy_service_imports_point_to_new_packages():
    assert LegacyServiceBase.__name__ == "ServiceBase"
    assert LegacyApprovalService is ApprovalService
    assert LegacyAuthService is AuthService
    assert LegacyAuditService is AuditService
    assert LegacyProjectService is ProjectService
    assert LegacyProjectResourceService is ProjectResourceService
    assert LegacyRegisterService is RegisterService
    assert LegacyTaskService is TaskService
    assert LegacyResourceService is ResourceService
    assert LegacyCalendarService is CalendarService
    assert LegacySchedulingEngine is SchedulingEngine
    assert LegacyCPMTaskInfo is CPMTaskInfo
    assert LegacyWorkCalendarEngine is WorkCalendarEngine
    assert LegacyWorkCalendarService is WorkCalendarService
    assert LegacyReportingService is ReportingService
    assert LegacyBaselineService is BaselineService
    assert LegacyFinanceService is FinanceService


def test_services_module_delegates_to_modular_registration_builders():
    text = (
        Path(__file__).resolve().parents[1] / "src" / "infra" / "composition" / "app_container.py"
    ).read_text(
        encoding="utf-8",
        errors="ignore",
    )

    assert "from src.infra.composition.platform_registry import build_platform_service_bundle" in text
    assert "from src.infra.composition.repositories import build_repository_bundle" in text
    assert "build_repository_bundle(session)" in text
    assert "build_platform_service_bundle(session, repositories)" in text
    assert "build_inventory_procurement_service_bundle(platform_services)" in text
    assert "build_maintenance_management_service_bundle(" in text
    assert "build_project_management_service_bundle(" in text


def test_service_registration_package_is_split_by_platform_and_module():
    root = Path(__file__).resolve().parents[1] / "src" / "infra" / "composition"

    assert (root / "__init__.py").exists()
    assert (root / "repositories.py").exists()
    assert (root / "platform_registry.py").exists()
    assert (root / "inventory_registry.py").exists()
    assert (root / "maintenance_registry.py").exists()
    assert (root / "project_registry.py").exists()
