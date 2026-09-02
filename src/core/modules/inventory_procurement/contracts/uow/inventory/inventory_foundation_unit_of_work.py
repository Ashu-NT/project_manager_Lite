from __future__ import annotations

from typing import Protocol

from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    ReorderPolicyRepository,
    StoreroomRepository,
    StorageLocationRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class InventoryFoundationUnitOfWork(UnitOfWork, Protocol):
    """One fresh transaction for Storeroom + Storage Location commands (P20), joined by Reorder
    Policy commands (P25) -- all three are owned by `InventoryFoundationService`'s own
    "foundation" capability, sharing the identical `inventory.manage`/`inventory.read` permission
    model and the same `storeroom`-scoped authorization checks, even though no single operation
    currently writes to more than one of these repositories at once."""

    storerooms: StoreroomRepository
    locations: StorageLocationRepository
    reorder_policies: ReorderPolicyRepository
    _enterprise_audit_service: EnterpriseAuditService


class InventoryFoundationUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> InventoryFoundationUnitOfWork: ...  # type: ignore[override]


__all__ = ["InventoryFoundationUnitOfWork", "InventoryFoundationUnitOfWorkFactory"]
