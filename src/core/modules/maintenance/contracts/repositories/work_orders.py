from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.maintenance.domain.work_orders.order import (
    MaintenanceWorkOrder,
    MaintenanceWorkOrderMaterialRequirement,
    MaintenanceWorkOrderTask,
    MaintenanceWorkOrderTaskStep,
)


class MaintenanceWorkOrderRepository(ABC):
    @abstractmethod
    def add(self, work_order: MaintenanceWorkOrder) -> None: ...

    @abstractmethod
    def update(self, work_order: MaintenanceWorkOrder) -> None: ...

    @abstractmethod
    def get(self, work_order_id: str) -> MaintenanceWorkOrder | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, work_order_code: str) -> MaintenanceWorkOrder | None: ...

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
    ) -> list[MaintenanceWorkOrder]: ...


class MaintenanceWorkOrderTaskRepository(ABC):
    @abstractmethod
    def add(self, work_order_task: MaintenanceWorkOrderTask) -> None: ...

    @abstractmethod
    def update(self, work_order_task: MaintenanceWorkOrderTask) -> None: ...

    @abstractmethod
    def get(self, work_order_task_id: str) -> MaintenanceWorkOrderTask | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id: str | None = None,
        status: str | None = None,
        assigned_employee_id: str | None = None,
        assigned_team_id: str | None = None,
    ) -> list[MaintenanceWorkOrderTask]: ...


class MaintenanceWorkOrderTaskStepRepository(ABC):
    @abstractmethod
    def add(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None: ...

    @abstractmethod
    def update(self, work_order_task_step: MaintenanceWorkOrderTaskStep) -> None: ...

    @abstractmethod
    def get(self, work_order_task_step_id: str) -> MaintenanceWorkOrderTaskStep | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_task_id: str | None = None,
        status: str | None = None,
    ) -> list[MaintenanceWorkOrderTaskStep]: ...


class MaintenanceWorkOrderMaterialRequirementRepository(ABC):
    @abstractmethod
    def add(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None: ...

    @abstractmethod
    def update(self, material_requirement: MaintenanceWorkOrderMaterialRequirement) -> None: ...

    @abstractmethod
    def get(self, material_requirement_id: str) -> MaintenanceWorkOrderMaterialRequirement | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        work_order_id: str | None = None,
        procurement_status: str | None = None,
        preferred_storeroom_id: str | None = None,
        stock_item_id: str | None = None,
    ) -> list[MaintenanceWorkOrderMaterialRequirement]: ...
