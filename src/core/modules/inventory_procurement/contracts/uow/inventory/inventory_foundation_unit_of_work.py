from __future__ import annotations

from typing import Protocol

from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StoreroomRepository,
    StorageLocationRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class InventoryFoundationUnitOfWork(UnitOfWork, Protocol):
    """One fresh transaction for Storeroom + Storage Location commands (P20)."""

    storerooms: StoreroomRepository
    locations: StorageLocationRepository
    _enterprise_audit_service: EnterpriseAuditService


class InventoryFoundationUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> InventoryFoundationUnitOfWork: ...  # type: ignore[override]


__all__ = ["InventoryFoundationUnitOfWork", "InventoryFoundationUnitOfWorkFactory"]
