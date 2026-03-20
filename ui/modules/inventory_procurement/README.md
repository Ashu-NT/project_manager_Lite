# Inventory & Procurement UI

This package now mirrors the core module structure so related UI code stays
grouped by domain:

- `item_master/`: item dialogs and the items workspace
- `inventory/`: storeroom dialogs and the storerooms workspace
- `procurement/`: requisitions, purchase orders, receiving, and shared dialogs
- `reservation/`: reservation dialogs and workspace
- `stock_control/`: stock and movement dialogs/workspaces
- `shared/`: UI-only helper functions shared across workspaces

Top-level modules such as `ui.modules.inventory_procurement.items_tab` remain as
compatibility aliases for existing imports and tests. New code should import
from the domain subpackages directly.
