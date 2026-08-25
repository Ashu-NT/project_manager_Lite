from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.platform.domain.tenant.modules.subscription import ModuleEntitlementRecord


class ModuleEntitlementRepository(ABC):
    @abstractmethod
    def get_for_organization(
        self,
        organization_id: str,
        module_code: str,
    ) -> ModuleEntitlementRecord | None: ...

    @abstractmethod
    def list_all_for_organization(self, organization_id: str) -> list[ModuleEntitlementRecord]: ...

    @abstractmethod
    def upsert_for_organization(self, organization_id: str, record: ModuleEntitlementRecord) -> None: ...

    @abstractmethod
    def list_all_for_organization_in_tenant(self, organization_id: str) -> list[ModuleEntitlementRecord]:
        """Tenant-administration/provisioning read: any organization within the
        authenticated tenant, not only the currently active one."""
        ...

    @abstractmethod
    def upsert_for_organization_in_tenant(self, organization_id: str, record: ModuleEntitlementRecord) -> None:
        """Tenant-administration/provisioning write: explicitly allowed to
        initialize a specified organization within the authenticated tenant
        before that organization becomes active. Ordinary runtime callers must
        keep using upsert_for_organization (active organization only)."""
        ...

    @abstractmethod
    def get_for_organization_in_tenant(
        self, organization_id: str, module_code: str
    ) -> ModuleEntitlementRecord | None:
        """Tenant-administration write-path read: any organization within the authenticated
        tenant, not only the currently active one (P5B prerequisite -- explicit, non-active-org
        module entitlement mutation needs to read that organization's own current state first).
        """
        ...

    @abstractmethod
    def get(self, module_code: str) -> ModuleEntitlementRecord | None: ...

    @abstractmethod
    def list_all(self) -> list[ModuleEntitlementRecord]: ...

    @abstractmethod
    def upsert(self, record: ModuleEntitlementRecord) -> None: ...


__all__ = [
    "ModuleEntitlementRepository",
]
