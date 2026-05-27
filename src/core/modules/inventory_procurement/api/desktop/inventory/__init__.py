from src.core.modules.inventory_procurement.api.desktop.inventory.api import (
    InventoryProcurementInventoryDesktopApi,
    build_inventory_procurement_inventory_desktop_api,
)
from src.core.modules.inventory_procurement.api.desktop.inventory.models import (
    InventoryAdjustmentCommand,
    InventoryCycleCountCompleteCommand,
    InventoryCycleCountCreateCommand,
    InventoryCycleCountDesktopDto,
    InventoryCycleCountStatusDescriptor,
    InventoryFoundationMetricDescriptor,
    InventoryFoundationSignalDesktopDto,
    InventoryFoundationSnapshotDesktopDto,
    InventoryIssueCommand,
    InventoryLocationCreateCommand,
    InventoryLocationTypeDescriptor,
    InventoryLocationUpdateCommand,
    InventoryModuleLinkDescriptor,
    InventoryOpeningBalanceCommand,
    InventoryReorderPolicyDesktopDto,
    InventoryReorderPolicyUpsertCommand,
    InventoryReturnCommand,
    InventoryStorageLocationDesktopDto,
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
    serialize_cycle_count,
    serialize_foundation_signal,
    serialize_reorder_policy,
    serialize_storage_location,
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
_serialize_cycle_count = serialize_cycle_count
_serialize_foundation_signal = serialize_foundation_signal
_serialize_reorder_policy = serialize_reorder_policy
_serialize_storage_location = serialize_storage_location
_serialize_storeroom = serialize_storeroom
_serialize_transaction = serialize_transaction

__all__ = [
    "InventoryAdjustmentCommand",
    "InventoryCycleCountCompleteCommand",
    "InventoryCycleCountCreateCommand",
    "InventoryCycleCountDesktopDto",
    "InventoryCycleCountStatusDescriptor",
    "InventoryCatalogItemOptionDescriptor",
    "InventoryFoundationMetricDescriptor",
    "InventoryFoundationSignalDesktopDto",
    "InventoryFoundationSnapshotDesktopDto",
    "InventoryIssueCommand",
    "InventoryLocationCreateCommand",
    "InventoryLocationTypeDescriptor",
    "InventoryLocationUpdateCommand",
    "InventoryModuleLinkDescriptor",
    "InventoryOpeningBalanceCommand",
    "InventoryProcurementInventoryDesktopApi",
    "InventoryReorderPolicyDesktopDto",
    "InventoryReorderPolicyUpsertCommand",
    "InventoryReturnCommand",
    "InventorySiteOptionDescriptor",
    "InventoryStorageLocationDesktopDto",
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
