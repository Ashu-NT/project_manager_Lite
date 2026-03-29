from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from core.modules.maintenance_management.domain import MaintenanceLocation, MaintenanceSystem


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


__all__ = [
    "MaintenanceLocationRepository",
    "MaintenanceSystemRepository",
]
