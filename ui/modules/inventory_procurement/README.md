# Inventory & Procurement UI

This package now mirrors the core module structure so related UI code stays
grouped by domain:

- `item_master/`: item dialogs and the items workspace
- `inventory/`: storeroom dialogs and the storerooms workspace
- `data_exchange/`: import wizard and raw CSV export workspace
- `procurement/`: requisitions, purchase orders, receiving, and shared dialogs
- `reporting/`: stock and procurement export workspace
- `reservation/`: reservation dialogs and workspace
- `stock_control/`: stock and movement dialogs/workspaces
- `shared/`: UI-only helper functions shared across workspaces

Import inventory UI code from the domain subpackages directly, or from the
package exports in `ui.modules.inventory_procurement`.
