from __future__ import annotations

import logging
from time import perf_counter

from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from src.core.platform.access import AccessControlService
from src.core.platform.integration.module_registry import ModuleRegistry
from src.core.platform.integration.resolver import IntegrationResolver
from src.core.platform.approval import ApprovalService
from src.core.platform.audit import AuditService
from src.core.platform.auth import AuthService
from src.core.platform.auth.domain.session import UserSessionContext
from src.core.platform.data_exchange import MasterDataExchangeService
from src.core.platform.documents import DocumentService
from src.core.platform.modules import ModuleCatalogService
from src.core.platform.department import DepartmentService
from src.core.platform.employee import EmployeeService
from src.core.platform.org import OrganizationService
from src.core.platform.site import SiteService
from src.core.platform.party import PartyService
from src.core.platform.time.application import TimeService
from src.core.platform.runtime_tracking import RuntimeExecutionService
from src.core.modules.inventory_procurement import (
    ProcurementService,
    InventoryDataExchangeService,
    MaintenanceMaterialService,
    InventoryReferenceService,
    InventoryReportingService,
    PurchasingService,
)
from src.core.modules.inventory_procurement.application.catalog import (
    ItemCategoryService,
    ItemMasterService,
)
from src.core.modules.inventory_procurement.application.inventory import (
    InventoryFoundationService,
    InventoryService,
    ReservationService,
    StockControlService,
)
from src.core.modules.maintenance import (
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
    MaintenanceSensorExceptionService,
    MaintenanceSensorReadingService,
    MaintenanceSensorService,
    MaintenanceSensorSourceMappingService,
    MaintenanceSystemService,
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkOrderTaskStepService,
    MaintenanceWorkRequestService,
)
from src.core.modules.maintenance.application.common import (
    MaintenanceRuntimeContractCatalogService,
)
from src.core.modules.maintenance.infrastructure.reporting import (
    MaintenanceReportingService,
)
from src.core.modules.project_management.application.scheduling.baselines.baseline_service import (
    BaselineService,
)
from src.core.modules.project_management.application.dashboard import DashboardService
from src.core.modules.project_management.application.financials import CostService, FinanceService
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.scheduling import (
    CalendarService,
    SchedulingEngine,
)
from src.core.modules.project_management.infrastructure.importers import DataImportService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.application.collaboration import CollaborationService
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.timesheets import TimesheetService
from src.core.modules.project_management.application.resources.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.platform.calendar.application.enterprise_calendar_service import EnterpriseCalendarService
from src.core.platform.calendar.application.working_rule_service import WorkingRuleService
from src.core.platform.calendar.application.calendar_exception_service import CalendarExceptionService
from src.core.platform.calendar.application.recurring_event_service import RecurringEventService
from src.core.platform.calendar.application.shift_pattern_service import ShiftPatternService
from src.core.platform.calendar.application.calendar_assignment_service import CalendarAssignmentService
from src.core.platform.calendar.application.enterprise_calendar_resolver import EnterpriseCalendarResolver
from src.core.platform.calendar.application.working_time_calculator import WorkingTimeCalculator
from src.core.modules.project_management.application.resources.resource_capacity_calculator import ResourceCapacityCalculator
from src.core.modules.project_management.application.resources.enterprise_resource_availability import EnterpriseResourceAvailabilityService
from src.core.modules.project_management.infrastructure.collaboration_store import TaskCollaborationStore
from src.infra.composition.inventory_registry import build_inventory_procurement_service_bundle
from src.infra.composition.maintenance_registry import build_maintenance_service_bundle
from src.infra.composition.platform_registry import build_platform_service_bundle
from src.infra.composition.project_registry import build_project_management_service_bundle
from src.infra.composition.repositories import build_repository_bundle


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServiceGraph:
    session: Session
    user_session: UserSessionContext
    platform_runtime_application_service: PlatformRuntimeApplicationService
    module_runtime_service: ModuleRuntimeService
    module_catalog_service: ModuleCatalogService
    module_registry: ModuleRegistry
    integration_resolver: IntegrationResolver
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
    inventory_foundation_service: InventoryFoundationService
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
    work_calendar_engine: CalendarProtocol  # GlobalCalendarShim — enterprise-backed
    scheduling_engine: SchedulingEngine
    reporting_service: ReportingService
    baseline_service: BaselineService
    dashboard_service: DashboardService
    portfolio_service: PortfolioService
    register_service: RegisterService
    project_resource_service: ProjectResourceService
    data_import_service: DataImportService
    task_collaboration_store: TaskCollaborationStore
    assignment_skill_validator: AssignmentSkillValidator
    enterprise_calendar_service: EnterpriseCalendarService | None
    working_rule_service: WorkingRuleService | None
    calendar_exception_service: CalendarExceptionService | None
    recurring_event_service: RecurringEventService | None
    shift_pattern_service: ShiftPatternService | None
    calendar_assignment_service: CalendarAssignmentService | None
    enterprise_calendar_resolver: EnterpriseCalendarResolver | None
    working_time_calculator: WorkingTimeCalculator | None
    resource_capacity_calculator: ResourceCapacityCalculator | None
    enterprise_resource_availability: EnterpriseResourceAvailabilityService | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "session": self.session,
            "user_session": self.user_session,
            "platform_runtime_application_service": self.platform_runtime_application_service,
            "module_runtime_service": self.module_runtime_service,
            "module_catalog_service": self.module_catalog_service,
            "module_registry": self.module_registry,
            "integration_resolver": self.integration_resolver,
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
            "inventory_foundation_service": self.inventory_foundation_service,
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
            "scheduling_engine": self.scheduling_engine,
            "reporting_service": self.reporting_service,
            "baseline_service": self.baseline_service,
            "dashboard_service": self.dashboard_service,
            "portfolio_service": self.portfolio_service,
            "register_service": self.register_service,
            "project_resource_service": self.project_resource_service,
            "data_import_service": self.data_import_service,
            "task_collaboration_store": self.task_collaboration_store,
            "assignment_skill_validator": self.assignment_skill_validator,
            "enterprise_calendar_service": self.enterprise_calendar_service,
            "working_rule_service": self.working_rule_service,
            "calendar_exception_service": self.calendar_exception_service,
            "recurring_event_service": self.recurring_event_service,
            "shift_pattern_service": self.shift_pattern_service,
            "calendar_assignment_service": self.calendar_assignment_service,
            "enterprise_calendar_resolver": self.enterprise_calendar_resolver,
            "working_time_calculator": self.working_time_calculator,
            "resource_capacity_calculator": self.resource_capacity_calculator,
            # Registered as "resource_availability_service" so build_desktop_api_registry picks it up.
            # The old ResourceAvailabilityService (uses WorkCalendarEngine) is no longer the default.
            "resource_availability_service": self.enterprise_resource_availability,
        }


def build_service_graph(session: Session) -> ServiceGraph:
    started = perf_counter()
    logger.debug("Service graph build begin session_type=%s", type(session).__name__)
    repositories = build_repository_bundle(session)
    logger.debug(
        "Repository bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    platform_services = build_platform_service_bundle(session, repositories)
    logger.debug(
        "Platform service bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    inventory_procurement_services = build_inventory_procurement_service_bundle(platform_services)
    logger.debug(
        "Inventory/Procurement service bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    maintenance_services = build_maintenance_service_bundle(
        platform_services,
        inventory_procurement_services,
    )
    logger.debug(
        "Maintenance service bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    project_management_services = build_project_management_service_bundle(
        session,
        repositories,
        platform_services,
    )
    logger.debug(
        "Project Management service bundle built duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    _module_registry = ModuleRegistry(platform_services.module_runtime_service)
    _integration_resolver = IntegrationResolver(_module_registry)
    graph = ServiceGraph(
        session=session,
        user_session=platform_services.user_session,
        platform_runtime_application_service=platform_services.platform_runtime_application_service,
        module_runtime_service=platform_services.module_runtime_service,
        module_catalog_service=platform_services.module_catalog_service,
        module_registry=_module_registry,
        integration_resolver=_integration_resolver,
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
        inventory_foundation_service=inventory_procurement_services.inventory_foundation_service,
        inventory_service=inventory_procurement_services.inventory_service,
        inventory_stock_service=inventory_procurement_services.inventory_stock_service,
        inventory_reservation_service=inventory_procurement_services.inventory_reservation_service,
        inventory_procurement_service=inventory_procurement_services.inventory_procurement_service,
        inventory_purchasing_service=inventory_procurement_services.inventory_purchasing_service,
        maintenance_runtime_contract_catalog_service=maintenance_services.maintenance_runtime_contract_catalog_service,
        maintenance_asset_service=maintenance_services.maintenance_asset_service,
        maintenance_asset_component_service=maintenance_services.maintenance_asset_component_service,
        maintenance_document_service=maintenance_services.maintenance_document_service,
        maintenance_downtime_event_service=maintenance_services.maintenance_downtime_event_service,
        maintenance_failure_code_service=maintenance_services.maintenance_failure_code_service,
        maintenance_integration_source_service=maintenance_services.maintenance_integration_source_service,
        maintenance_labor_service=maintenance_services.maintenance_labor_service,
        maintenance_location_service=maintenance_services.maintenance_location_service,
        maintenance_preventive_generation_service=maintenance_services.maintenance_preventive_generation_service,
        maintenance_preventive_plan_service=maintenance_services.maintenance_preventive_plan_service,
        maintenance_preventive_plan_task_service=maintenance_services.maintenance_preventive_plan_task_service,
        maintenance_reliability_service=maintenance_services.maintenance_reliability_service,
        maintenance_reporting_service=maintenance_services.maintenance_reporting_service,
        maintenance_sensor_exception_service=maintenance_services.maintenance_sensor_exception_service,
        maintenance_sensor_service=maintenance_services.maintenance_sensor_service,
        maintenance_sensor_reading_service=maintenance_services.maintenance_sensor_reading_service,
        maintenance_sensor_source_mapping_service=maintenance_services.maintenance_sensor_source_mapping_service,
        maintenance_system_service=maintenance_services.maintenance_system_service,
        maintenance_task_step_template_service=maintenance_services.maintenance_task_step_template_service,
        maintenance_task_template_service=maintenance_services.maintenance_task_template_service,
        maintenance_work_request_service=maintenance_services.maintenance_work_request_service,
        maintenance_work_order_service=maintenance_services.maintenance_work_order_service,
        maintenance_work_order_material_requirement_service=maintenance_services.maintenance_work_order_material_requirement_service,
        maintenance_work_order_task_service=maintenance_services.maintenance_work_order_task_service,
        maintenance_work_order_task_step_service=maintenance_services.maintenance_work_order_task_step_service,
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
        scheduling_engine=project_management_services.scheduling_engine,
        reporting_service=project_management_services.reporting_service,
        baseline_service=project_management_services.baseline_service,
        dashboard_service=project_management_services.dashboard_service,
        portfolio_service=project_management_services.portfolio_service,
        register_service=project_management_services.register_service,
        project_resource_service=project_management_services.project_resource_service,
        data_import_service=project_management_services.data_import_service,
        task_collaboration_store=project_management_services.task_collaboration_store,
        assignment_skill_validator=project_management_services.assignment_skill_validator,
        enterprise_calendar_service=platform_services.enterprise_calendar_service,
        working_rule_service=platform_services.working_rule_service,
        calendar_exception_service=platform_services.calendar_exception_service,
        recurring_event_service=platform_services.recurring_event_service,
        shift_pattern_service=platform_services.shift_pattern_service,
        calendar_assignment_service=platform_services.calendar_assignment_service,
        enterprise_calendar_resolver=platform_services.enterprise_calendar_resolver,
        working_time_calculator=platform_services.working_time_calculator,
        resource_capacity_calculator=project_management_services.resource_capacity_calculator,
        enterprise_resource_availability=project_management_services.enterprise_resource_availability,
    )
    logger.debug(
        "Service graph build complete duration_ms=%.1f",
        (perf_counter() - started) * 1000,
    )
    return graph


def build_service_dict(session: Session) -> dict[str, Any]:
    started = perf_counter()
    graph = build_service_graph(session)
    services = graph.as_dict()
    logger.debug(
        "Service dictionary build complete service_count=%s duration_ms=%.1f",
        len(services),
        (perf_counter() - started) * 1000,
    )
    return services
