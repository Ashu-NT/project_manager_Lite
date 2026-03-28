"""Item master UI workspaces and dialogs."""

from ui.modules.inventory_procurement.item_master.categories_tab import InventoryItemCategoriesTab
from ui.modules.inventory_procurement.item_master.category_dialogs import (
    InventoryItemCategoryEditDialog,
)
from ui.modules.inventory_procurement.item_master.document_link_dialogs import (
    InventoryItemDocumentLinkDialog,
)
from ui.modules.inventory_procurement.item_master.item_dialogs import InventoryItemEditDialog
from ui.modules.inventory_procurement.item_master.items_tab import InventoryItemsTab

__all__ = [
    "InventoryItemCategoriesTab",
    "InventoryItemCategoryEditDialog",
    "InventoryItemDocumentLinkDialog",
    "InventoryItemEditDialog",
    "InventoryItemsTab",
]
