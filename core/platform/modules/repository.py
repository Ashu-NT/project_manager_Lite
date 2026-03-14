from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleEntitlementRecord:
    module_code: str
    licensed: bool
    enabled: bool
    lifecycle_status: str = "inactive"


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


__all__ = ["ModuleEntitlementRecord", "ModuleEntitlementRepository"]
