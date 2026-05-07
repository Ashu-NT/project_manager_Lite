from src.core.modules.inventory_procurement.api.desktop.inventory.api import (
    InventoryProcurementInventoryDesktopApi,
    build_inventory_procurement_inventory_desktop_api,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryAdjustmentCommand,
    InventoryIssueCommand,
    InventoryOpeningBalanceCommand,
    InventoryReturnCommand,
    InventoryStockBalanceDesktopDto,
    InventoryStockTransactionDesktopDto,
    InventoryStoreroomCreateCommand,
    InventoryStoreroomDesktopDto,
    InventoryStoreroomStatusDescriptor,
    InventoryStoreroomUpdateCommand,
    InventoryTransactionTypeDescriptor,
    InventoryTransferCommand,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.serializers import (
    serialize_balance,
    serialize_storeroom,
    serialize_transaction,
)
from src.core.modules.inventory_procurement.api.desktop.shared_options import (
    InventoryCatalogItemOptionDescriptor,
    InventorySiteOptionDescriptor,
    InventoryStoreroomOptionDescriptor,
    serialize_item_option,
    serialize_site_option,
    serialize_storeroom_option,
)

_serialize_item_option = serialize_item_option
_serialize_site = serialize_site_option
_serialize_storeroom_option = serialize_storeroom_option
_serialize_balance = serialize_balance
_serialize_storeroom = serialize_storeroom
_serialize_transaction = serialize_transaction

__all__ = [
    "InventoryAdjustmentCommand",
    "InventoryCatalogItemOptionDescriptor",
    "InventoryIssueCommand",
    "InventoryOpeningBalanceCommand",
    "InventoryProcurementInventoryDesktopApi",
    "InventoryReturnCommand",
    "InventorySiteOptionDescriptor",
    "InventoryStockBalanceDesktopDto",
    "InventoryStockTransactionDesktopDto",
    "InventoryStoreroomCreateCommand",
    "InventoryStoreroomDesktopDto",
    "InventoryStoreroomOptionDescriptor",
    "InventoryStoreroomStatusDescriptor",
    "InventoryStoreroomUpdateCommand",
    "InventoryTransactionTypeDescriptor",
    "InventoryTransferCommand",
    "build_inventory_procurement_inventory_desktop_api",
]
