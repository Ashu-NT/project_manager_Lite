from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from src.core.platform.modules.domain.module_entitlement import ModuleEntitlement
from src.core.platform.modules.domain.subscription import ModuleEntitlementRecord


class SupportsModuleEntitlements(Protocol):
    def get_entitlement(self, module_code: str) -> ModuleEntitlement | None: ...

    def is_enabled(self, module_code: str) -> bool: ...


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
    def get(self, module_code: str) -> ModuleEntitlementRecord | None: ...

    @abstractmethod
    def list_all(self) -> list[ModuleEntitlementRecord]: ...

    @abstractmethod
    def upsert(self, record: ModuleEntitlementRecord) -> None: ...


__all__ = [
    "ModuleEntitlementRepository",
    "SupportsModuleEntitlements",
]
