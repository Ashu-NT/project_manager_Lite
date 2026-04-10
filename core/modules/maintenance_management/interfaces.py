from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceDowntimeEvent,
    MaintenanceFailureCode,
    MaintenanceIntegrationSource,
    MaintenanceLocation,
    MaintenancePreventivePlanInstance,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceSensorException,
    MaintenanceSensor,
    MaintenanceSensorReading,
    MaintenanceSensorSourceMapping,
    MaintenanceTaskStepTemplate,
    MaintenanceTaskTemplate,
    MaintenanceWorkOrderMaterialRequirement,
    MaintenanceSystem,
    MaintenanceWorkOrder,
    MaintenanceWorkOrderTask,
    MaintenanceWorkOrderTaskStep,
    MaintenanceWorkRequest,
)


class MaintenanceLocationRepository(ABC):
    @abstractmethod
    def add(self, location: MaintenanceLocation) -> None: ...

    @abstractmethod
    def update(self, location: MaintenanceLocation) -> None: ...

    @abstractmethod
    def get(self, location_id: str) -> Optional[MaintenanceLocation]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        location_code: str,
    ) -> Optional[MaintenanceLocation]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        parent_location_id: str | None = None,
    ) -> List[MaintenanceLocation]: ...


class MaintenanceSystemRepository(ABC):
    @abstractmethod
    def add(self, system: MaintenanceSystem) -> None: ...

    @abstractmethod
    def update(self, system: MaintenanceSystem) -> None: ...

    @abstractmethod
    def get(self, system_id: str) -> Optional[MaintenanceSystem]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        system_code: str,
    ) -> Optional[MaintenanceSystem]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        parent_system_id: str | None = None,
    ) -> List[MaintenanceSystem]: ...


class MaintenanceAssetRepository(ABC):
    @abstractmethod
    def add(self, asset: MaintenanceAsset) -> None: ...

    @abstractmethod
    def update(self, asset: MaintenanceAsset) -> None: ...

    @abstractmethod
    def get(self, asset_id: str) -> Optional[MaintenanceAsset]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        asset_code: str,
    ) -> Optional[MaintenanceAsset]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        system_id: str | None = None,
        parent_asset_id: str | None = None,
        asset_category: str | None = None,
    ) -> List[MaintenanceAsset]: ...


class MaintenanceAssetComponentRepository(ABC):
    @abstractmethod
    def add(self, component: MaintenanceAssetComponent) -> None: ...

    @abstractmethod
    def update(self, component: MaintenanceAssetComponent) -> None: ...

    @abstractmethod
    def get(self, component_id: str) -> Optional[MaintenanceAssetComponent]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        component_code: str,
    ) -> Optional[MaintenanceAssetComponent]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        asset_id: str | None = None,
        parent_component_id: str | None = None,
        component_type: str | None = None,
    ) -> List[MaintenanceAssetComponent]: ...


class MaintenanceSensorRepository(ABC):
    @abstractmethod
    def add(self, sensor: MaintenanceSensor) -> None: ...

    @abstractmethod
    def update(self, sensor: MaintenanceSensor) -> None: ...

    @abstractmethod
    def get(self, sensor_id: str) -> Optional[MaintenanceSensor]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        sensor_code: str,
    ) -> Optional[MaintenanceSensor]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        sensor_type: str | None = None,
        source_type: str | None = None,
    ) -> List[MaintenanceSensor]: ...


class MaintenanceSensorReadingRepository(ABC):
    @abstractmethod
    def add(self, sensor_reading: MaintenanceSensorReading) -> None: ...

    @abstractmethod
    def get(self, sensor_reading_id: str) -> Optional[MaintenanceSensorReading]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        sensor_id: str | None = None,
        quality_state: str | None = None,
        source_batch_id: str | None = None,
        reading_from=None,
        reading_to=None,
    ) -> List[MaintenanceSensorReading]: ...


class MaintenanceIntegrationSourceRepository(ABC):
    @abstractmethod
    def add(self, integration_source: MaintenanceIntegrationSource) -> None: ...

    @abstractmethod
    def update(self, integration_source: MaintenanceIntegrationSource) -> None: ...

    @abstractmethod
    def get(self, integration_source_id: str) -> Optional[MaintenanceIntegrationSource]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        integration_code: str,
    ) -> Optional[MaintenanceIntegrationSource]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        integration_type: str | None = None,
    ) -> List[MaintenanceIntegrationSource]: ...


class MaintenanceSensorSourceMappingRepository(ABC):
    @abstractmethod
    def add(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None: ...

    @abstractmethod
    def update(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None: ...

    @abstractmethod
    def get(self, sensor_source_mapping_id: str) -> Optional[MaintenanceSensorSourceMapping]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        integration_source_id: str | None = None,
        sensor_id: str | None = None,
        active_only: bool | None = None,
    ) -> List[MaintenanceSensorSourceMapping]: ...


class MaintenanceSensorExceptionRepository(ABC):
    @abstractmethod
    def add(self, sensor_exception: MaintenanceSensorException) -> None: ...

    @abstractmethod
    def update(self, sensor_exception: MaintenanceSensorException) -> None: ...

    @abstractmethod
    def get(self, sensor_exception_id: str) -> Optional[MaintenanceSensorException]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        sensor_id: str | None = None,
        integration_source_id: str | None = None,
        source_mapping_id: str | None = None,
        exception_type: str | None = None,
        status: str | None = None,
        source_batch_id: str | None = None,
    ) -> List[MaintenanceSensorException]: ...


class MaintenanceFailureCodeRepository(ABC):
    @abstractmethod
    def add(self, failure_code: MaintenanceFailureCode) -> None: ...

    @abstractmethod
    def update(self, failure_code: MaintenanceFailureCode) -> None: ...

    @abstractmethod
    def get(self, failure_code_id: str) -> Optional[MaintenanceFailureCode]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        failure_code: str,
    ) -> Optional[MaintenanceFailureCode]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        code_type: str | None = None,
        parent_code_id: str | None = None,
    ) -> List[MaintenanceFailureCode]: ...


class MaintenanceDowntimeEventRepository(ABC):
    @abstractmethod
    def add(self, downtime_event: MaintenanceDowntimeEvent) -> None: ...

    @abstractmethod
    def update(self, downtime_event: MaintenanceDowntimeEvent) -> None: ...

    @abstractmethod
    def get(self, downtime_event_id: str) -> Optional[MaintenanceDowntimeEvent]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id: str | None = None,
        asset_id: str | None = None,
        system_id: str | None = None,
        downtime_type: str | None = None,
        reason_code: str | None = None,
        open_only: bool | None = None,
        started_from=None,
        started_to=None,
    ) -> List[MaintenanceDowntimeEvent]: ...


class MaintenanceWorkRequestRepository(ABC):
    @abstractmethod
    def add(self, work_request: MaintenanceWorkRequest) -> None: ...

    @abstractmethod
    def update(self, work_request: MaintenanceWorkRequest) -> None: ...

    @abstractmethod
    def get(self, work_request_id: str) -> Optional[MaintenanceWorkRequest]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        work_request_code: str,
    ) -> Optional[MaintenanceWorkRequest]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        requested_by_user_id: str | None = None,
        triaged_by_user_id: str | None = None,
    ) -> List[MaintenanceWorkRequest]: ...


class MaintenanceWorkOrderRepository(ABC):
    @abstractmethod
    def add(self, work_order: MaintenanceWorkOrder) -> None: ...

    @abstractmethod
    def update(self, work_order: MaintenanceWorkOrder) -> None: ...

    @abstractmethod
    def get(self, work_order_id: str) -> Optional[MaintenanceWorkOrder]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        work_order_code: str,
    ) -> Optional[MaintenanceWorkOrder]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        location_id: str | None = None,
        status: str | None = None,
        priority: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
        planner_user_id: str | None = None,
        supervisor_user_id: str | None = None,
        work_order_type: str | None = None,
        is_preventive: bool | None = None,
        is_emergency: bool | None = None,
    ) -> List[MaintenanceWorkOrder]: ...


class MaintenanceWorkOrderTaskRepository(ABC):
    @abstractmethod
    def add(self, work_order_task: MaintenanceWorkOrderTask) -> None: ...

    @abstractmethod
    def update(self, work_order_task: MaintenanceWorkOrderTask) -> None: ...

    @abstractmethod
    def get(self, work_order_task_id: str) -> Optional[MaintenanceWorkOrderTask]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id: str | None = None,
        status: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
    ) -> List[MaintenanceWorkOrderTask]: ...


class MaintenanceWorkOrderTaskStepRepository(ABC):
    @abstractmethod
    def add(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None: ...

    @abstractmethod
    def update(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None: ...

    @abstractmethod
    def get(self, work_order_task_step_id: str) -> Optional[MaintenanceWorkOrderTaskStep]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_task_id: str | None = None,
        status: str | None = None,
    ) -> List[MaintenanceWorkOrderTaskStep]: ...


class MaintenanceWorkOrderMaterialRequirementRepository(ABC):
    @abstractmethod
    def add(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None: ...

    @abstractmethod
    def update(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None: ...

    @abstractmethod
    def get(self, material_requirement_id: str) -> Optional[MaintenanceWorkOrderMaterialRequirement]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id: str | None = None,
        procurement_status: str | None = None,
        preferred_storeroom_id: str | None = None,
        stock_item_id: str | None = None,
    ) -> List[MaintenanceWorkOrderMaterialRequirement]: ...


class MaintenanceTaskTemplateRepository(ABC):
    @abstractmethod
    def add(self, task_template: MaintenanceTaskTemplate) -> None: ...

    @abstractmethod
    def update(self, task_template: MaintenanceTaskTemplate) -> None: ...

    @abstractmethod
    def get(self, task_template_id: str) -> Optional[MaintenanceTaskTemplate]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        task_template_code: str,
    ) -> Optional[MaintenanceTaskTemplate]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        maintenance_type: str | None = None,
        template_status: str | None = None,
    ) -> List[MaintenanceTaskTemplate]: ...


class MaintenanceTaskStepTemplateRepository(ABC):
    @abstractmethod
    def add(self, task_step_template: MaintenanceTaskStepTemplate) -> None: ...

    @abstractmethod
    def update(self, task_step_template: MaintenanceTaskStepTemplate) -> None: ...

    @abstractmethod
    def get(self, task_step_template_id: str) -> Optional[MaintenanceTaskStepTemplate]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        task_template_id: str | None = None,
        active_only: bool | None = None,
    ) -> List[MaintenanceTaskStepTemplate]: ...


class MaintenancePreventivePlanRepository(ABC):
    @abstractmethod
    def add(self, preventive_plan: MaintenancePreventivePlan) -> None: ...

    @abstractmethod
    def update(self, preventive_plan: MaintenancePreventivePlan) -> None: ...

    @abstractmethod
    def get(self, preventive_plan_id: str) -> Optional[MaintenancePreventivePlan]: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        plan_code: str,
    ) -> Optional[MaintenancePreventivePlan]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        asset_id: str | None = None,
        component_id: str | None = None,
        system_id: str | None = None,
        status: str | None = None,
        plan_type: str | None = None,
        trigger_mode: str | None = None,
        sensor_id: str | None = None,
    ) -> List[MaintenancePreventivePlan]: ...


class MaintenancePreventivePlanTaskRepository(ABC):
    @abstractmethod
    def add(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None: ...

    @abstractmethod
    def update(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None: ...

    @abstractmethod
    def get(self, preventive_plan_task_id: str) -> Optional[MaintenancePreventivePlanTask]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        plan_id: str | None = None,
        task_template_id: str | None = None,
    ) -> List[MaintenancePreventivePlanTask]: ...


class MaintenancePreventivePlanInstanceRepository(ABC):
    @abstractmethod
    def add(self, preventive_instance: MaintenancePreventivePlanInstance) -> None: ...

    @abstractmethod
    def update(self, preventive_instance: MaintenancePreventivePlanInstance) -> None: ...

    @abstractmethod
    def delete(self, preventive_instance_id: str) -> None: ...

    @abstractmethod
    def get(self, preventive_instance_id: str) -> Optional[MaintenancePreventivePlanInstance]: ...

    @abstractmethod
    def get_by_generated_work_order_id(
        self,
        organization_id: str,
        work_order_id: str,
    ) -> Optional[MaintenancePreventivePlanInstance]: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        plan_id: str | None = None,
        status: str | None = None,
        generated_work_request_id: str | None = None,
        generated_work_order_id: str | None = None,
    ) -> List[MaintenancePreventivePlanInstance]: ...


__all__ = [
    "MaintenanceAssetRepository",
    "MaintenanceAssetComponentRepository",
    "MaintenanceDowntimeEventRepository",
    "MaintenanceFailureCodeRepository",
    "MaintenanceIntegrationSourceRepository",
    "MaintenanceLocationRepository",
    "MaintenancePreventivePlanRepository",
    "MaintenancePreventivePlanInstanceRepository",
    "MaintenancePreventivePlanTaskRepository",
    "MaintenanceSensorExceptionRepository",
    "MaintenanceSensorReadingRepository",
    "MaintenanceSensorRepository",
    "MaintenanceSensorSourceMappingRepository",
    "MaintenanceSystemRepository",
    "MaintenanceTaskStepTemplateRepository",
    "MaintenanceTaskTemplateRepository",
    "MaintenanceWorkOrderRepository",
    "MaintenanceWorkOrderMaterialRequirementRepository",
    "MaintenanceWorkOrderTaskRepository",
    "MaintenanceWorkOrderTaskStepRepository",
    "MaintenanceWorkRequestRepository",
]
