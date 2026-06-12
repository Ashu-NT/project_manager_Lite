from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.org.domain import Organization


class OrganizationRepository(ABC):
    @abstractmethod
    def add(self, organization: Organization) -> None: ...

    @abstractmethod
    def update(self, organization: Organization) -> None: ...

    @abstractmethod
    def get(self, organization_id: str) -> Organization | None: ...

    @abstractmethod
    def get_by_code(self, organization_code: str) -> Organization | None: ...

    @abstractmethod
    def get_active(self) -> Organization | None: ...

    @abstractmethod
    def list_all(self, *, active_only: bool | None = None) -> list[Organization]: ...

    @abstractmethod
    def list_for_tenant(self, tenant_id: str, *, active_only: bool | None = None) -> list[Organization]: ...


__all__ = [
    "OrganizationRepository",
]
