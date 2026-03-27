from __future__ import annotations

from sqlalchemy.orm import Session

from core.modules.inventory_procurement.interfaces import StockBalanceRepository, StockTransactionRepository
from core.modules.inventory_procurement.services.inventory import InventoryService
from core.modules.inventory_procurement.services.item_master import ItemMasterService
from core.modules.inventory_procurement.services.stock_control.stock_adjustments import StockControlAdjustmentMixin
from core.modules.inventory_procurement.services.stock_control.stock_movements import StockControlMovementMixin
from core.modules.inventory_procurement.services.stock_control.stock_queries import StockControlQueryMixin
from core.modules.inventory_procurement.services.stock_control.stock_support import StockControlSupportMixin
from core.platform.common.interfaces import OrganizationRepository


class StockControlService(
    StockControlSupportMixin,
    StockControlQueryMixin,
    StockControlAdjustmentMixin,
    StockControlMovementMixin,
):
    """Inventory stock control service composed from focused mixins."""

    def __init__(
        self,
        session: Session,
        balance_repo: StockBalanceRepository,
        transaction_repo: StockTransactionRepository,
        *,
        organization_repo: OrganizationRepository,
        item_service: ItemMasterService,
        inventory_service: InventoryService,
        user_session=None,
        audit_service=None,
    ):
        self._session = session
        self._balance_repo = balance_repo
        self._transaction_repo = transaction_repo
        self._organization_repo = organization_repo
        self._item_service = item_service
        self._inventory_service = inventory_service
        self._user_session = user_session
        self._audit_service = audit_service


__all__ = ["StockControlService"]
