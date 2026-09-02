from __future__ import annotations

from typing import Protocol

from src.core.modules.inventory_procurement.contracts.repositories.catalog import (
    InventoryItemCategoryRepository,
    StockItemRepository,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class InventoryCatalogUnitOfWork(UnitOfWork, Protocol):

    items: StockItemRepository
    categories: InventoryItemCategoryRepository
    _enterprise_audit_service: EnterpriseAuditService


class InventoryCatalogUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> InventoryCatalogUnitOfWork: ...  # type: ignore[override]


__all__ = ["InventoryCatalogUnitOfWork", "InventoryCatalogUnitOfWorkFactory"]
