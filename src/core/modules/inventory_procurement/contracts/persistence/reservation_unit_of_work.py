from __future__ import annotations

from typing import Protocol

from src.core.modules.inventory_procurement.application.inventory.stock_control_service import (
    StockControlService,
)
from src.core.modules.inventory_procurement.contracts.repositories.inventory import (
    StockBalanceRepository,
    StockReservationRepository,
    StockTransactionRepository,
)
from src.core.platform.application.history.activity.activity_service import ActivityService
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.shared.persistence.unit_of_work import UnitOfWork, UnitOfWorkFactory


class InventoryReservationUnitOfWork(UnitOfWork, Protocol):
    reservations: StockReservationRepository
    balances: StockBalanceRepository
    stock_transactions: StockTransactionRepository
    stock_service: StockControlService
    # Same leading-underscore name `record_audit_entry`/`record_activity`'s owner-duck-type
    # lookup requires -- see `PlatformUnitOfWork`'s own identical fields for the full rationale.
    _enterprise_audit_service: EnterpriseAuditService
    _activity_service: ActivityService


class InventoryReservationUnitOfWorkFactory(UnitOfWorkFactory, Protocol):
    def create(self, *, context) -> InventoryReservationUnitOfWork: ...  # type: ignore[override]


__all__ = ["InventoryReservationUnitOfWork", "InventoryReservationUnitOfWorkFactory"]
