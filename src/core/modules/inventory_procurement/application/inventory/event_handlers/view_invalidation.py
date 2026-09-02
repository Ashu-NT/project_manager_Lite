from __future__ import annotations

from src.core.modules.inventory_procurement.domain.inventory.foundation_events import (
    InventoryReorderPolicyConfigured,
    LocationCreated,
    LocationProfileUpdated,
    StoreroomCreated,
    StoreroomProfileUpdated,
    StoreroomStatusChanged,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

INVENTORY_CATEGORY = "inventory"
STOREROOM_LIST_SCOPE_CODE = "storeroom_list"
LOCATION_LIST_SCOPE_CODE = "location_list"
REORDER_POLICY_LIST_SCOPE_CODE = "reorder_policy_list"

_OrgTarget = tuple[str, str]


def build_storeroom_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`storeroom_list` is a single org-wide projection consumed both as the Inventory
    workspace's own Storeroom master list/detail AND as the `storeroom_options` selector
    embedded in Pricing/Procurement/Reservations (proven from source: both are populated from
    the same underlying storeroom rows, always stale together -- P20 §9 explicitly forbids a
    second target for the same projection). Every Storeroom fact (create, profile update, status
    change) invalidates it -- there is no narrower Storeroom read-model to split out.

    Deduplicated per (tenant_id, organization_id) target, transaction-scoped (P18B-FIX): keyed
    by (transaction correlation_id, target identity), cleared the moment a new correlation_id
    arrives."""

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_OrgTarget] = set()

    def handle_storeroom_event(
        event: StoreroomCreated | StoreroomProfileUpdated | StoreroomStatusChanged,
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
                category=INVENTORY_CATEGORY,
                scope_code=STOREROOM_LIST_SCOPE_CODE,
                entity_type="storeroom",
                entity_id=event.storeroom_id,
            )
        )

    return handle_storeroom_event


def build_location_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`location_list` is a single org-wide projection -- the Inventory workspace's own Storage
    Location list/detail under its "foundation" panel. Proven from source: no other Inventory/
    Procurement workspace presenter references Storage Location data at all (unlike Storeroom,
    which is also consumed as a reference-options selector elsewhere)."""

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_OrgTarget] = set()

    def handle_location_event(
        event: LocationCreated | LocationProfileUpdated,
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
                category=INVENTORY_CATEGORY,
                scope_code=LOCATION_LIST_SCOPE_CODE,
                entity_type="storage_location",
                entity_id=event.location_id,
            )
        )

    return handle_location_event


def build_reorder_policy_list_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`reorder_policy_list` is a single org-wide projection -- the Inventory workspace's own
    "Foundation" panel (`list_reorder_policies`/`build_foundation_snapshot`), optionally filtered
    by item/storeroom/location at query time but never cached as a separate per-item or
    per-storeroom projection. Proven from source: no other Inventory/Procurement workspace
    presenter references the `ReorderPolicy` entity at all -- the Dashboard/Pricing "reorder
    required" low-stock signal is computed entirely from `StockItem`'s own embedded
    `reorder_point`/`min_qty` fields (already covered by P24's `InventoryItemProfileUpdated`),
    never from this table."""

    current_correlation_id: list[str | None] = [None]
    notified_targets: set[_OrgTarget] = set()

    def handle_reorder_policy_event(
        event: InventoryReorderPolicyConfigured,
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
                category=INVENTORY_CATEGORY,
                scope_code=REORDER_POLICY_LIST_SCOPE_CODE,
                entity_type="inventory_reorder_policy",
                entity_id=event.policy_id,
            )
        )

    return handle_reorder_policy_event


__all__ = [
    "build_storeroom_list_view_invalidation_handler",
    "build_location_list_view_invalidation_handler",
    "build_reorder_policy_list_view_invalidation_handler",
    "INVENTORY_CATEGORY",
    "STOREROOM_LIST_SCOPE_CODE",
    "LOCATION_LIST_SCOPE_CODE",
    "REORDER_POLICY_LIST_SCOPE_CODE",
]
