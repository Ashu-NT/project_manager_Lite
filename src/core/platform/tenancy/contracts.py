from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.tenancy.domain.tenant import Tenant
from src.core.platform.tenancy.domain.user_tenant_membership import UserTenantMembership


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


class UserTenantMembershipRepository(ABC):
    @abstractmethod
    def add(self, membership: UserTenantMembership) -> None: ...

    @abstractmethod
    def get(self, user_id: str, tenant_id: str) -> UserTenantMembership | None: ...

    @abstractmethod
    def is_active_member(self, user_id: str, tenant_id: str) -> bool: ...

    @abstractmethod
    def list_tenant_ids_for_user(self, user_id: str) -> list[str]: ...

    @abstractmethod
    def list_users_for_tenant(self, tenant_id: str) -> list[UserTenantMembership]: ...

    @abstractmethod
    def deactivate(self, user_id: str, tenant_id: str) -> None: ...


__all__ = ["TenantRepository", "UserTenantMembershipRepository"]
