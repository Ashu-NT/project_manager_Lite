from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.core.modules.inventory_procurement.application.inventory.stock_control_service import (
        StockControlService,
    )
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    CycleCountRepository,
    ReorderPolicyRepository,
    StockBalanceRepository,
    StockTransactionRepository,
    StoreroomRepository,
    StorageLocationRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class InventoryFoundationUnitOfWork(UnitOfWork, Protocol):

    storerooms: StoreroomRepository
    locations: StorageLocationRepository
    reorder_policies: ReorderPolicyRepository
    cycle_counts: CycleCountRepository
    balances: StockBalanceRepository
    stock_transactions: StockTransactionRepository
    stock_service: StockControlService
    _enterprise_audit_service: EnterpriseAuditService
    _activity_service: ActivityService


class InventoryFoundationUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> InventoryFoundationUnitOfWork: ...  # type: ignore[override]


__all__ = ["InventoryFoundationUnitOfWork", "InventoryFoundationUnitOfWorkFactory"]
