from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.maintenance.domain.assets.asset import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
)
from src.core.modules.maintenance.domain.locations.location import (
    MaintenanceLocation,
    MaintenanceSystem,
)


class MaintenanceLocationRepository(ABC):
    @abstractmethod
    def add(self, location: MaintenanceLocation) -> None: ...

    @abstractmethod
    def update(self, location: MaintenanceLocation) -> None: ...

    @abstractmethod
    def get(self, location_id: str) -> MaintenanceLocation | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, location_code: str) -> MaintenanceLocation | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        parent_location_id: str | None = None,
    ) -> list[MaintenanceLocation]: ...


class MaintenanceSystemRepository(ABC):
    @abstractmethod
    def add(self, system: MaintenanceSystem) -> None: ...

    @abstractmethod
    def update(self, system: MaintenanceSystem) -> None: ...

    @abstractmethod
    def get(self, system_id: str) -> MaintenanceSystem | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, system_code: str) -> MaintenanceSystem | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        site_id: str | None = None,
        location_id: str | None = None,
        parent_system_id: str | None = None,
    ) -> list[MaintenanceSystem]: ...


class MaintenanceAssetRepository(ABC):
    @abstractmethod
    def add(self, asset: MaintenanceAsset) -> None: ...

    @abstractmethod
    def update(self, asset: MaintenanceAsset) -> None: ...

    @abstractmethod
    def get(self, asset_id: str) -> MaintenanceAsset | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, asset_code: str) -> MaintenanceAsset | None: ...

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
    ) -> list[MaintenanceAsset]: ...


class MaintenanceAssetComponentRepository(ABC):
    @abstractmethod
    def add(self, component: MaintenanceAssetComponent) -> None: ...

    @abstractmethod
    def update(self, component: MaintenanceAssetComponent) -> None: ...

    @abstractmethod
    def get(self, component_id: str) -> MaintenanceAssetComponent | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, component_code: str) -> MaintenanceAssetComponent | None: ...

    @abstractmethod
    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
        asset_id: str | None = None,
        parent_component_id: str | None = None,
        component_type: str | None = None,
    ) -> list[MaintenanceAssetComponent]: ...
