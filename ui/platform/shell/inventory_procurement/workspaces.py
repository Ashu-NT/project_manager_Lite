from __future__ import annotations

from ui.modules.inventory_procurement import (
    InventoryDataExchangeTab,
    InventoryDashboardTab,
    InventoryItemCategoriesTab,
    InventoryItemsTab,
    InventoryReportsTab,
    MovementsTab,
    PurchaseOrdersTab,
    ReceivingTab,
    ReservationsTab,
    RequisitionsTab,
    StockTab,
    StoreroomsTab,
)
from ui.platform.shell.common import (
    INVENTORY_PROCUREMENT_MODULE_CODE,
    INVENTORY_PROCUREMENT_MODULE_LABEL,
    ShellWorkspaceContext,
    WorkspaceDefinition,
    has_any_permission,
    has_permission,
)


def build_inventory_procurement_workspace_definitions(
    context: ShellWorkspaceContext,
) -> list[WorkspaceDefinition]:
    if not context.inventory_procurement_enabled or not has_permission(context.user_session, "inventory.read"):
        return []

    services = context.services
    definitions: list[WorkspaceDefinition] = [
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Overview",
            label="Inventory Dashboard",
            widget=InventoryDashboardTab(
                item_service=services["inventory_item_service"],
                inventory_service=services["inventory_service"],
                stock_service=services["inventory_stock_service"],
                reservation_service=services["inventory_reservation_service"],
                procurement_service=services["inventory_procurement_service"],
                purchasing_service=services["inventory_purchasing_service"],
                reference_service=services["inventory_reference_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Master Data",
            label="Items",
            widget=InventoryItemsTab(
                item_service=services["inventory_item_service"],
                category_service=services["inventory_item_category_service"],
                reference_service=services["inventory_reference_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Master Data",
            label="Item Categories",
            widget=InventoryItemCategoriesTab(
                category_service=services["inventory_item_category_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Operations",
            label="Reservations",
            widget=ReservationsTab(
                reservation_service=services["inventory_reservation_service"],
                item_service=services["inventory_item_service"],
                inventory_service=services["inventory_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Operations",
            label="Movements",
            widget=MovementsTab(
                stock_service=services["inventory_stock_service"],
                item_service=services["inventory_item_service"],
                inventory_service=services["inventory_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Master Data",
            label="Storerooms",
            widget=StoreroomsTab(
                inventory_service=services["inventory_service"],
                reference_service=services["inventory_reference_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Operations",
            label="Stock",
            widget=StockTab(
                stock_service=services["inventory_stock_service"],
                item_service=services["inventory_item_service"],
                inventory_service=services["inventory_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Procurement",
            label="Requisitions",
            widget=RequisitionsTab(
                procurement_service=services["inventory_procurement_service"],
                item_service=services["inventory_item_service"],
                inventory_service=services["inventory_service"],
                reference_service=services["inventory_reference_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Procurement",
            label="Purchase Orders",
            widget=PurchaseOrdersTab(
                purchasing_service=services["inventory_purchasing_service"],
                procurement_service=services["inventory_procurement_service"],
                item_service=services["inventory_item_service"],
                inventory_service=services["inventory_service"],
                reference_service=services["inventory_reference_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
        WorkspaceDefinition(
            module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
            module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
            group_label="Procurement",
            label="Receiving",
            widget=ReceivingTab(
                purchasing_service=services["inventory_purchasing_service"],
                item_service=services["inventory_item_service"],
                inventory_service=services["inventory_service"],
                reference_service=services["inventory_reference_service"],
                platform_runtime_application_service=context.platform_runtime_application_service,
                user_session=context.user_session,
                parent=context.parent,
            ),
        ),
    ]

    if has_any_permission(context.user_session, "import.manage", "report.export"):
        definitions.append(
            WorkspaceDefinition(
                module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
                module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
                group_label="Control",
                label="Data Exchange",
                widget=InventoryDataExchangeTab(
                    data_exchange_service=services["inventory_data_exchange_service"],
                    platform_runtime_application_service=context.platform_runtime_application_service,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    if has_permission(context.user_session, "report.export"):
        definitions.append(
            WorkspaceDefinition(
                module_code=INVENTORY_PROCUREMENT_MODULE_CODE,
                module_label=INVENTORY_PROCUREMENT_MODULE_LABEL,
                group_label="Control",
                label="Reports",
                widget=InventoryReportsTab(
                    reporting_service=services["inventory_reporting_service"],
                    reference_service=services["inventory_reference_service"],
                    inventory_service=services["inventory_service"],
                    platform_runtime_application_service=context.platform_runtime_application_service,
                    user_session=context.user_session,
                    parent=context.parent,
                ),
            )
        )

    return definitions


__all__ = ["build_inventory_procurement_workspace_definitions"]
