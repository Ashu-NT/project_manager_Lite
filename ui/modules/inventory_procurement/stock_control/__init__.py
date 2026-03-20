"""Stock control UI workspaces and dialogs."""

from ui.modules.inventory_procurement.stock_control.movement_dialogs import (
    StockMovementDialog,
    StockTransferDialog,
)
from ui.modules.inventory_procurement.stock_control.movements_tab import MovementsTab
from ui.modules.inventory_procurement.stock_control.stock_dialogs import (
    OpeningBalanceDialog,
    StockAdjustmentDialog,
)
from ui.modules.inventory_procurement.stock_control.stock_tab import StockTab

__all__ = [
    "StockMovementDialog",
    "StockTransferDialog",
    "MovementsTab",
    "OpeningBalanceDialog",
    "StockAdjustmentDialog",
    "StockTab",
]
