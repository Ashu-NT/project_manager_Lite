from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.platform.access import AccessControlService
from core.platform.approval import ApprovalService
from core.platform.audit import AuditService
from core.platform.auth import AuthService
from core.platform.auth.session import UserSessionContext
from core.platform.data_exchange import MasterDataExchangeService
from core.platform.documents import DocumentService
from core.platform.modules.service import ModuleCatalogService
from core.platform.org import DepartmentService, EmployeeService, OrganizationService, SiteService
from core.platform.party import PartyService
from core.platform.time import TimeService
from core.platform.runtime_tracking import RuntimeExecutionService
from core.modules.inventory_procurement import (
    ProcurementService,
    InventoryDataExchangeService,
    MaintenanceMaterialService,
    InventoryReferenceService,
    InventoryService,
    InventoryReportingService,
    ItemCategoryService,
    ItemMasterService,
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
from core.modules.project_management.services.calendar import CalendarService
from core.modules.project_management.services.collaboration import CollaborationService
from core.modules.project_management.services.cost import CostService
from core.modules.project_management.services.dashboard import DashboardService
from core.modules.project_management.services.finance import FinanceService
from core.modules.project_management.services.import_service import DataImportService
from core.modules.project_management.services.portfolio import PortfolioService
from core.modules.project_management.services.project import ProjectResourceService, ProjectService
from core.modules.project_management.services.register import RegisterService
from core.modules.project_management.services.reporting import ReportingService
from core.modules.project_management.services.resource import ResourceService
from core.modules.project_management.services.scheduling import SchedulingEngine
from core.modules.project_management.services.task import TaskService
from core.modules.project_management.services.timesheet import TimesheetService
from core.modules.project_management.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from infra.modules.project_management.collaboration_store import TaskCollaborationStore
from src.infra.composition.inventory_registry import build_inventory_procurement_service_bundle
from src.infra.composition.maintenance_registry import build_maintenance_management_service_bundle
from src.infra.composition.platform_registry import build_platform_service_bundle
from src.infra.composition.project_registry import build_project_management_service_bundle
from src.infra.composition.repositories import build_repository_bundle


@dataclass(frozen=True)
class ServiceGraph:
    session: Session
    user_session: UserSessionContext
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_runtime_service: ModuleRuntimeService
    module_catalog_service: ModuleCatalogService
    time_service: TimeService
    auth_service: AuthService
    organization_service: OrganizationService
    document_service: DocumentService
    party_service: PartyService
    department_service: DepartmentService
    site_service: SiteService
    employee_service: EmployeeService
    master_data_exchange_service: MasterDataExchangeService
    runtime_execution_service: RuntimeExecutionService
    inventory_reference_service: InventoryReferenceService
    inventory_data_exchange_service: InventoryDataExchangeService
    inventory_reporting_service: InventoryReportingService
    inventory_item_category_service: ItemCategoryService
    inventory_item_service: ItemMasterService
    inventory_maintenance_material_service: MaintenanceMaterialService
    inventory_service: InventoryService
    inventory_stock_service: StockControlService
    inventory_reservation_service: ReservationService
    inventory_procurement_service: ProcurementService
    inventory_purchasing_service: PurchasingService
    maintenance_runtime_contract_catalog_service: MaintenanceRuntimeContractCatalogService
    maintenance_asset_service: MaintenanceAssetService
    maintenance_asset_component_service: MaintenanceAssetComponentService
    maintenance_document_service: MaintenanceDocumentService
    maintenance_downtime_event_service: MaintenanceDowntimeEventService
    maintenance_failure_code_service: MaintenanceFailureCodeService
    maintenance_integration_source_service: MaintenanceIntegrationSourceService
    maintenance_labor_service: MaintenanceLaborService
    maintenance_location_service: MaintenanceLocationService
    maintenance_preventive_generation_service: MaintenancePreventiveGenerationService
    maintenance_preventive_plan_service: MaintenancePreventivePlanService
    maintenance_preventive_plan_task_service: MaintenancePreventivePlanTaskService
    maintenance_reliability_service: MaintenanceReliabilityService
    maintenance_reporting_service: MaintenanceReportingService
    maintenance_sensor_exception_service: MaintenanceSensorExceptionService
    maintenance_sensor_service: MaintenanceSensorService
    maintenance_sensor_reading_service: MaintenanceSensorReadingService
    maintenance_sensor_source_mapping_service: MaintenanceSensorSourceMappingService
    maintenance_system_service: MaintenanceSystemService
    maintenance_task_step_template_service: MaintenanceTaskStepTemplateService
    maintenance_task_template_service: MaintenanceTaskTemplateService
    maintenance_work_request_service: MaintenanceWorkRequestService
    maintenance_work_order_service: MaintenanceWorkOrderService
    maintenance_work_order_material_requirement_service: MaintenanceWorkOrderMaterialRequirementService
    maintenance_work_order_task_service: MaintenanceWorkOrderTaskService
    maintenance_work_order_task_step_service: MaintenanceWorkOrderTaskStepService
    access_service: AccessControlService
    audit_service: AuditService
    approval_service: ApprovalService
    collaboration_service: CollaborationService
    project_service: ProjectService
    task_service: TaskService
    timesheet_service: TimesheetService
    calendar_service: CalendarService
    resource_service: ResourceService
    cost_service: CostService
    finance_service: FinanceService
    work_calendar_engine: WorkCalendarEngine
    work_calendar_service: WorkCalendarService
    scheduling_engine: SchedulingEngine
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    portfolio_service: PortfolioService
    register_service: RegisterService
    project_resource_service: ProjectResourceService
    data_import_service: DataImportService
    task_collaboration_store: TaskCollaborationStore

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "user_session": self.user_session,
            "platform_runtime_application_service": self.platform_runtime_application_service,
            "module_runtime_service": self.module_runtime_service,
            "module_catalog_service": self.module_catalog_service,
            "time_service": self.time_service,
            "auth_service": self.auth_service,
            "organization_service": self.organization_service,
            "document_service": self.document_service,
            "party_service": self.party_service,
            "department_service": self.department_service,
            "site_service": self.site_service,
            "employee_service": self.employee_service,
            "master_data_exchange_service": self.master_data_exchange_service,
            "runtime_execution_service": self.runtime_execution_service,
            "inventory_reference_service": self.inventory_reference_service,
            "inventory_data_exchange_service": self.inventory_data_exchange_service,
            "inventory_reporting_service": self.inventory_reporting_service,
            "inventory_item_category_service": self.inventory_item_category_service,
            "inventory_item_service": self.inventory_item_service,
            "inventory_maintenance_material_service": self.inventory_maintenance_material_service,
            "inventory_service": self.inventory_service,
            "inventory_stock_service": self.inventory_stock_service,
            "inventory_reservation_service": self.inventory_reservation_service,
            "inventory_procurement_service": self.inventory_procurement_service,
            "inventory_purchasing_service": self.inventory_purchasing_service,
            "maintenance_runtime_contract_catalog_service": self.maintenance_runtime_contract_catalog_service,
            "maintenance_asset_service": self.maintenance_asset_service,
            "maintenance_asset_component_service": self.maintenance_asset_component_service,
            "maintenance_document_service": self.maintenance_document_service,
            "maintenance_downtime_event_service": self.maintenance_downtime_event_service,
            "maintenance_failure_code_service": self.maintenance_failure_code_service,
            "maintenance_integration_source_service": self.maintenance_integration_source_service,
            "maintenance_labor_service": self.maintenance_labor_service,
            "maintenance_location_service": self.maintenance_location_service,
            "maintenance_preventive_generation_service": self.maintenance_preventive_generation_service,
            "maintenance_preventive_plan_service": self.maintenance_preventive_plan_service,
            "maintenance_preventive_plan_task_service": self.maintenance_preventive_plan_task_service,
            "maintenance_reliability_service": self.maintenance_reliability_service,
            "maintenance_reporting_service": self.maintenance_reporting_service,
            "maintenance_sensor_exception_service": self.maintenance_sensor_exception_service,
            "maintenance_sensor_service": self.maintenance_sensor_service,
            "maintenance_sensor_reading_service": self.maintenance_sensor_reading_service,
            "maintenance_sensor_source_mapping_service": self.maintenance_sensor_source_mapping_service,
            "maintenance_system_service": self.maintenance_system_service,
            "maintenance_task_step_template_service": self.maintenance_task_step_template_service,
            "maintenance_task_template_service": self.maintenance_task_template_service,
            "maintenance_work_request_service": self.maintenance_work_request_service,
            "maintenance_work_order_service": self.maintenance_work_order_service,
            "maintenance_work_order_material_requirement_service": self.maintenance_work_order_material_requirement_service,
            "maintenance_work_order_task_service": self.maintenance_work_order_task_service,
            "maintenance_work_order_task_step_service": self.maintenance_work_order_task_step_service,
            "access_service": self.access_service,
            "audit_service": self.audit_service,
            "approval_service": self.approval_service,
            "collaboration_service": self.collaboration_service,
            "project_service": self.project_service,
            "task_service": self.task_service,
            "timesheet_service": self.timesheet_service,
            "calendar_service": self.calendar_service,
            "resource_service": self.resource_service,
            "cost_service": self.cost_service,
            "finance_service": self.finance_service,
            "work_calendar_engine": self.work_calendar_engine,
            "work_calendar_service": self.work_calendar_service,
            "scheduling_engine": self.scheduling_engine,
            "reporting_service": self.reporting_service,
            "baseline_service": self.baseline_service,
            "dashboard_service": self.dashboard_service,
            "portfolio_service": self.portfolio_service,
            "register_service": self.register_service,
            "project_resource_service": self.project_resource_service,
            "data_import_service": self.data_import_service,
            "task_collaboration_store": self.task_collaboration_store,
        }


def build_service_graph(session: Session) -> ServiceGraph:
    repositories = build_repository_bundle(session)
    platform_services = build_platform_service_bundle(session, repositories)
    inventory_procurement_services = build_inventory_procurement_service_bundle(platform_services)
    maintenance_management_services = build_maintenance_management_service_bundle(
        platform_services,
        inventory_procurement_services,
    )
    project_management_services = build_project_management_service_bundle(
        session,
        repositories,
        platform_services,
    )
    return ServiceGraph(
        session=session,
        user_session=platform_services.user_session,
        platform_runtime_application_service=platform_services.platform_runtime_application_service,
        module_runtime_service=platform_services.module_runtime_service,
        module_catalog_service=platform_services.module_catalog_service,
        time_service=project_management_services.time_service,
        auth_service=platform_services.auth_service,
        organization_service=platform_services.organization_service,
        document_service=platform_services.document_service,
        party_service=platform_services.party_service,
        department_service=platform_services.department_service,
        site_service=platform_services.site_service,
        employee_service=platform_services.employee_service,
        master_data_exchange_service=platform_services.master_data_exchange_service,
        runtime_execution_service=platform_services.runtime_execution_service,
        inventory_reference_service=inventory_procurement_services.inventory_reference_service,
        inventory_data_exchange_service=inventory_procurement_services.inventory_data_exchange_service,
        inventory_reporting_service=inventory_procurement_services.inventory_reporting_service,
        inventory_item_category_service=inventory_procurement_services.inventory_item_category_service,
        inventory_item_service=inventory_procurement_services.inventory_item_service,
        inventory_maintenance_material_service=inventory_procurement_services.inventory_maintenance_material_service,
        inventory_service=inventory_procurement_services.inventory_service,
        inventory_stock_service=inventory_procurement_services.inventory_stock_service,
        inventory_reservation_service=inventory_procurement_services.inventory_reservation_service,
        inventory_procurement_service=inventory_procurement_services.inventory_procurement_service,
        inventory_purchasing_service=inventory_procurement_services.inventory_purchasing_service,
        maintenance_runtime_contract_catalog_service=maintenance_management_services.maintenance_runtime_contract_catalog_service,
        maintenance_asset_service=maintenance_management_services.maintenance_asset_service,
        maintenance_asset_component_service=maintenance_management_services.maintenance_asset_component_service,
        maintenance_document_service=maintenance_management_services.maintenance_document_service,
        maintenance_downtime_event_service=maintenance_management_services.maintenance_downtime_event_service,
        maintenance_failure_code_service=maintenance_management_services.maintenance_failure_code_service,
        maintenance_integration_source_service=maintenance_management_services.maintenance_integration_source_service,
        maintenance_labor_service=maintenance_management_services.maintenance_labor_service,
        maintenance_location_service=maintenance_management_services.maintenance_location_service,
        maintenance_preventive_generation_service=maintenance_management_services.maintenance_preventive_generation_service,
        maintenance_preventive_plan_service=maintenance_management_services.maintenance_preventive_plan_service,
        maintenance_preventive_plan_task_service=maintenance_management_services.maintenance_preventive_plan_task_service,
        maintenance_reliability_service=maintenance_management_services.maintenance_reliability_service,
        maintenance_reporting_service=maintenance_management_services.maintenance_reporting_service,
        maintenance_sensor_exception_service=maintenance_management_services.maintenance_sensor_exception_service,
        maintenance_sensor_service=maintenance_management_services.maintenance_sensor_service,
        maintenance_sensor_reading_service=maintenance_management_services.maintenance_sensor_reading_service,
        maintenance_sensor_source_mapping_service=maintenance_management_services.maintenance_sensor_source_mapping_service,
        maintenance_system_service=maintenance_management_services.maintenance_system_service,
        maintenance_task_step_template_service=maintenance_management_services.maintenance_task_step_template_service,
        maintenance_task_template_service=maintenance_management_services.maintenance_task_template_service,
        maintenance_work_request_service=maintenance_management_services.maintenance_work_request_service,
        maintenance_work_order_service=maintenance_management_services.maintenance_work_order_service,
        maintenance_work_order_material_requirement_service=maintenance_management_services.maintenance_work_order_material_requirement_service,
        maintenance_work_order_task_service=maintenance_management_services.maintenance_work_order_task_service,
        maintenance_work_order_task_step_service=maintenance_management_services.maintenance_work_order_task_step_service,
        access_service=platform_services.access_service,
        audit_service=platform_services.audit_service,
        approval_service=platform_services.approval_service,
        collaboration_service=project_management_services.collaboration_service,
        project_service=project_management_services.project_service,
        task_service=project_management_services.task_service,
        timesheet_service=project_management_services.timesheet_service,
        calendar_service=project_management_services.calendar_service,
        resource_service=project_management_services.resource_service,
        cost_service=project_management_services.cost_service,
        finance_service=project_management_services.finance_service,
        work_calendar_engine=project_management_services.work_calendar_engine,
        work_calendar_service=project_management_services.work_calendar_service,
        scheduling_engine=project_management_services.scheduling_engine,
        reporting_service=project_management_services.reporting_service,
        baseline_service=project_management_services.baseline_service,
        dashboard_service=project_management_services.dashboard_service,
        portfolio_service=project_management_services.portfolio_service,
        register_service=project_management_services.register_service,
        project_resource_service=project_management_services.project_resource_service,
        data_import_service=project_management_services.data_import_service,
        task_collaboration_store=project_management_services.task_collaboration_store,
    )


def build_service_dict(session: Session) -> dict[str, Any]:
    return build_service_graph(session).as_dict()
