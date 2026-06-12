from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.tenancy.domain.tenant import Tenant


class TenantRepository(ABC):
    @abstractmethod
    def add(self, tenant: Tenant) -> None: ...

    @abstractmethod
    def update(self, tenant: Tenant) -> None: ...

    @abstractmethod
    def get(self, tenant_id: str) -> Tenant | None: ...

    @abstractmethod
    def get_by_code(self, tenant_code: str) -> Tenant | None: ...

    @abstractmethod
    def get_default(self) -> Tenant | None:
        """Return the first active tenant (bootstrap fallback)."""
        ...

    @abstractmethod
    def list_all(self, *, active_only: bool | None = None) -> list[Tenant]: ...


__all__ = ["TenantRepository"]
