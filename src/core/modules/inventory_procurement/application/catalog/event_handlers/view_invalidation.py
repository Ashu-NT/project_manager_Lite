from __future__ import annotations

from src.core.modules.inventory_procurement.domain.catalog.catalog_events import (
    InventoryItemCategoryCreated,
    InventoryItemCategoryProfileUpdated,
    InventoryItemCreated,
    InventoryItemProfileUpdated,
    InventoryItemStatusChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

INVENTORY_CATALOG_CATEGORY = "inventory_catalog"
ITEM_LIST_SCOPE_CODE = "item_list"
ITEM_CATEGORY_LIST_SCOPE_CODE = "item_category_list"

_OrgTarget = tuple[str, str]


def build_item_list_view_invalidation_handler(channel: ViewInvalidationChannel):

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_OrgTarget] = set()

    def handle_item_event(
        event: InventoryItemCreated | InventoryItemProfileUpdated | InventoryItemStatusChanged,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        target = (event.tenant_id, event.organization_id)
        if target in notified_targets:
            return
        notified_targets.add(target)

        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=INVENTORY_CATALOG_CATEGORY,
                scope_code=ITEM_LIST_SCOPE_CODE,
                entity_type="inventory_item",
                entity_id=event.item_id,
            )
        )

    return handle_item_event


def build_item_category_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`item_category_list` is a single org-wide projection -- Catalog's own Category master
    list/detail and the `category_options` selector are the same rows (`list_categories`/
    `search_categories`). Proven from source that Item list rows never embed a cached category
    name/hierarchy label: `search_items`'s category label (`_category_label`) and equipment/
    project-usage flags are computed live, at read time, from a freshly-queried category lookup
    on every call -- so a Category fact never needs to also invalidate `item_list` (P24 §16)."""

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_OrgTarget] = set()

    def handle_category_event(
        event: InventoryItemCategoryCreated | InventoryItemCategoryProfileUpdated,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_targets.clear()

        target = (event.tenant_id, event.organization_id)
        if target in notified_targets:
            return
        notified_targets.add(target)

        channel.notify(
            ViewInvalidationHint(
                scope=OrganizationScope(event.tenant_id, event.organization_id),
                category=INVENTORY_CATALOG_CATEGORY,
                scope_code=ITEM_CATEGORY_LIST_SCOPE_CODE,
                entity_type="inventory_item_category",
                entity_id=event.category_id,
            )
        )

    return handle_category_event


__all__ = [
    "build_item_list_view_invalidation_handler",
    "build_item_category_list_view_invalidation_handler",
    "INVENTORY_CATALOG_CATEGORY",
    "ITEM_LIST_SCOPE_CODE",
    "ITEM_CATEGORY_LIST_SCOPE_CODE",
]
