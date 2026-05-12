from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.modules.maintenance.domain.work_requests.request import (
    MaintenanceWorkRequest,
)


class MaintenanceWorkRequestRepository(ABC):
    @abstractmethod
    def add(self, work_request: MaintenanceWorkRequest) -> None: ...

    @abstractmethod
    def update(self, work_request: MaintenanceWorkRequest) -> None: ...

    @abstractmethod
    def get(self, work_request_id: str) -> MaintenanceWorkRequest | None: ...

    @abstractmethod
    def get_by_code(self, organization_id: str, work_request_code: str) -> MaintenanceWorkRequest | None: ...

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
    ) -> list[MaintenanceWorkRequest]: ...
