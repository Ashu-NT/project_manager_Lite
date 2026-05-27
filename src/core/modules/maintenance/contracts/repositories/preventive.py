from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.maintenance.domain.preventive.schedule import (
    MaintenancePreventivePlan,
    MaintenancePreventivePlanInstance,
    MaintenancePreventivePlanTask,
    MaintenanceTaskStepTemplate,
    MaintenanceTaskTemplate,
)


class MaintenanceTaskTemplateRepository(ABC):
    @abstractmethod
    def add(self, task_template: MaintenanceTaskTemplate) -> None: ...

    @abstractmethod
    def update(self, task_template: MaintenanceTaskTemplate) -> None: ...

    @abstractmethod
    def get(self, task_template_id: str) -> MaintenanceTaskTemplate | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, task_template_code: str) -> MaintenanceTaskTemplate | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        maintenance_type: str | None = None,
        template_status: str | None = None,
    ) -> list[MaintenanceTaskTemplate]: ...


class MaintenanceTaskStepTemplateRepository(ABC):
    @abstractmethod
    def add(self, task_step_template: MaintenanceTaskStepTemplate) -> None: ...

    @abstractmethod
    def update(self, task_step_template: MaintenanceTaskStepTemplate) -> None: ...

    @abstractmethod
    def get(self, task_step_template_id: str) -> MaintenanceTaskStepTemplate | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        task_template_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[MaintenanceTaskStepTemplate]: ...


class MaintenancePreventivePlanRepository(ABC):
    @abstractmethod
    def add(self, preventive_plan: MaintenancePreventivePlan) -> None: ...

    @abstractmethod
    def update(self, preventive_plan: MaintenancePreventivePlan) -> None: ...

    @abstractmethod
    def get(self, preventive_plan_id: str) -> MaintenancePreventivePlan | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, plan_code: str) -> MaintenancePreventivePlan | None: ...

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
    ) -> list[MaintenancePreventivePlan]: ...


class MaintenancePreventivePlanTaskRepository(ABC):
    @abstractmethod
    def add(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None: ...

    @abstractmethod
    def update(self, preventive_plan_task: MaintenancePreventivePlanTask) -> None: ...

    @abstractmethod
    def get(self, preventive_plan_task_id: str) -> MaintenancePreventivePlanTask | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        plan_id: str | None = None,
        task_template_id: str | None = None,
    ) -> list[MaintenancePreventivePlanTask]: ...


class MaintenancePreventivePlanInstanceRepository(ABC):
    @abstractmethod
    def add(self, preventive_instance: MaintenancePreventivePlanInstance) -> None: ...

    @abstractmethod
    def update(self, preventive_instance: MaintenancePreventivePlanInstance) -> None: ...

    @abstractmethod
    def delete(self, preventive_instance_id: str) -> None: ...

    @abstractmethod
    def get(self, preventive_instance_id: str) -> MaintenancePreventivePlanInstance | None: ...

    @abstractmethod
    def get_by_generated_work_order_id(
        self,
        organization_id: str,
        work_order_id: str,
    ) -> MaintenancePreventivePlanInstance | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        plan_id: str | None = None,
        status: str | None = None,
        generated_work_request_id: str | None = None,
        generated_work_order_id: str | None = None,
    ) -> list[MaintenancePreventivePlanInstance]: ...
