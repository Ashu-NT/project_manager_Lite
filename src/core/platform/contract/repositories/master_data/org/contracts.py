from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.domain.master_data.org import Organization


class OrganizationRepository(ABC):
    @abstractmethod
    def add(self, organization: Organization) -> None: ...

    @abstractmethod
    def update(self, organization: Organization) -> None: ...

    # --- bootstrap/admin paths (no tenant filter) ---

    @abstractmethod
    def get(self, organization_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_code(self, organization_code: str) -> Organization | None: ...

    @abstractmethod
    def get_active(self) -> Organization | None: ...

    @abstractmethod
    def list_all(self, *, active_only: bool | None = None) -> list[Organization]: ...

    # --- tenant-scoped runtime paths ---

    @abstractmethod
    def get_for_tenant(self, organization_id: str, tenant_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_code_for_tenant(self, organization_code: str, tenant_id: str) -> Organization | None: ...

    @abstractmethod
    def get_active_for_tenant(self, tenant_id: str) -> Organization | None: ...

    @abstractmethod
    def list_for_tenant(self, tenant_id: str, *, active_only: bool | None = None) -> list[Organization]: ...


__all__ = [
    "OrganizationRepository",
]
