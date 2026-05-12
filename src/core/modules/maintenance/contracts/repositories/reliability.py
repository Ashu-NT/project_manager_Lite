from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.maintenance.domain.reliability.monitoring import (
    MaintenanceDowntimeEvent,
    MaintenanceFailureCode,
    MaintenanceIntegrationSource,
    MaintenanceSensor,
    MaintenanceSensorException,
    MaintenanceSensorReading,
    MaintenanceSensorSourceMapping,
)


class MaintenanceSensorRepository(ABC):
    @abstractmethod
    def add(self, sensor: MaintenanceSensor) -> None: ...

    @abstractmethod
    def update(self, sensor: MaintenanceSensor) -> None: ...

    @abstractmethod
    def get(self, sensor_id: str) -> MaintenanceSensor | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, sensor_code: str) -> MaintenanceSensor | None: ...

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
    ) -> list[MaintenanceSensor]: ...


class MaintenanceSensorReadingRepository(ABC):
    @abstractmethod
    def add(self, sensor_reading: MaintenanceSensorReading) -> None: ...

    @abstractmethod
    def get(self, sensor_reading_id: str) -> MaintenanceSensorReading | None: ...

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
    ) -> list[MaintenanceSensorReading]: ...


class MaintenanceIntegrationSourceRepository(ABC):
    @abstractmethod
    def add(self, integration_source: MaintenanceIntegrationSource) -> None: ...

    @abstractmethod
    def update(self, integration_source: MaintenanceIntegrationSource) -> None: ...

    @abstractmethod
    def get(self, integration_source_id: str) -> MaintenanceIntegrationSource | None: ...

    @abstractmethod
    def get_by_code(
        self,
        organization_id: str,
        integration_code: str,
    ) -> MaintenanceIntegrationSource | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        integration_type: str | None = None,
    ) -> list[MaintenanceIntegrationSource]: ...


class MaintenanceSensorSourceMappingRepository(ABC):
    @abstractmethod
    def add(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None: ...

    @abstractmethod
    def update(self, sensor_source_mapping: MaintenanceSensorSourceMapping) -> None: ...

    @abstractmethod
    def get(self, sensor_source_mapping_id: str) -> MaintenanceSensorSourceMapping | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        integration_source_id: str | None = None,
        sensor_id: str | None = None,
        active_only: bool | None = None,
    ) -> list[MaintenanceSensorSourceMapping]: ...


class MaintenanceSensorExceptionRepository(ABC):
    @abstractmethod
    def add(self, sensor_exception: MaintenanceSensorException) -> None: ...

    @abstractmethod
    def update(self, sensor_exception: MaintenanceSensorException) -> None: ...

    @abstractmethod
    def get(self, sensor_exception_id: str) -> MaintenanceSensorException | None: ...

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
    ) -> list[MaintenanceSensorException]: ...


class MaintenanceFailureCodeRepository(ABC):
    @abstractmethod
    def add(self, failure_code: MaintenanceFailureCode) -> None: ...

    @abstractmethod
    def update(self, failure_code: MaintenanceFailureCode) -> None: ...

    @abstractmethod
    def get(self, failure_code_id: str) -> MaintenanceFailureCode | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, failure_code: str) -> MaintenanceFailureCode | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        code_type: str | None = None,
        parent_code_id: str | None = None,
    ) -> list[MaintenanceFailureCode]: ...


class MaintenanceDowntimeEventRepository(ABC):
    @abstractmethod
    def add(self, downtime_event: MaintenanceDowntimeEvent) -> None: ...

    @abstractmethod
    def update(self, downtime_event: MaintenanceDowntimeEvent) -> None: ...

    @abstractmethod
    def get(self, downtime_event_id: str) -> MaintenanceDowntimeEvent | None: ...

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
    ) -> list[MaintenanceDowntimeEvent]: ...
