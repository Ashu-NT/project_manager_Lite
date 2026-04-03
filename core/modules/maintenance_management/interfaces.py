from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceLocation,
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


__all__ = [
    "MaintenanceAssetRepository",
    "MaintenanceAssetComponentRepository",
    "MaintenanceLocationRepository",
    "MaintenanceSystemRepository",
    "MaintenanceWorkOrderRepository",
    "MaintenanceWorkOrderTaskRepository",
    "MaintenanceWorkOrderTaskStepRepository",
    "MaintenanceWorkRequestRepository",
]
