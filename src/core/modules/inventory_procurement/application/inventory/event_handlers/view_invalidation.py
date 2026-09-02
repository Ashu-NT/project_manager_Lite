from __future__ import annotations

from src.core.modules.inventory_procurement.domain.inventory.foundation_events import (
    InventoryReorderPolicyConfigured,
    LocationCreated,
    LocationProfileUpdated,
    StoreroomCreated,
    StoreroomProfileUpdated,
    StoreroomStatusChanged,
)
from src.core.modules.inventory_procurement.domain.inventory.reservation_events import (
    InventoryReservationCancelled,
    InventoryReservationConsumptionAdvanced,
    InventoryReservationCreated,
    InventoryReservationReleased,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.view_invalidation import (
    OrganizationScope,
    ResourceScope,
    ViewInvalidationChannel,
    ViewInvalidationHint,
)

INVENTORY_CATEGORY = "inventory"
STOREROOM_LIST_SCOPE_CODE = "storeroom_list"
LOCATION_LIST_SCOPE_CODE = "location_list"
REORDER_POLICY_LIST_SCOPE_CODE = "reorder_policy_list"

RESERVATION_CATEGORY = "inventory_reservation"
RESERVATION_MODULE_CODE = "inventory_procurement"
RESERVATION_ENTITY_TYPE = "stock_reservation"
RESERVATION_LIST_SCOPE_CODE = "reservation_list"
RESERVATION_DETAIL_SCOPE_CODE = "reservation_detail"
RESERVATION_OPEN_COUNT_SCOPE_CODE = "reservation_open_count"

_OrgTarget = tuple[str, str]
_ReservationOrgTarget = tuple[str, str, str]
_ReservationDetailTarget = tuple[str, str, str, str, str, str]

_FULLY_ISSUED_STATUS = "FULLY_ISSUED"


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


_ReservationEvent = (
    InventoryReservationCreated
    | InventoryReservationConsumptionAdvanced
    | InventoryReservationReleased
    | InventoryReservationCancelled
)


def _reservation_event_notifies_detail(event: _ReservationEvent) -> bool:
    # Mirrors Requisition's own `_requisition_event_notifies_detail` (P29): a reservation that
    # did not exist a moment ago cannot have a stale pre-existing detail view open anywhere.
    return not isinstance(event, InventoryReservationCreated)


def _reservation_event_notifies_open_count(event: _ReservationEvent) -> bool:
    # P30A/P30B: Dashboard's "Open Reservations" KPI counts ACTIVE + PARTIALLY_ISSUED. Created,
    # Released, and Cancelled always change membership. A partial issue (ACTIVE ->
    # PARTIALLY_ISSUED) does NOT change membership -- the reservation stays counted -- so only a
    # ConsumptionAdvanced whose `resulting_status` is FULLY_ISSUED (leaving the counted set)
    # actually staless the KPI.
    if isinstance(event, InventoryReservationConsumptionAdvanced):
        return event.resulting_status == _FULLY_ISSUED_STATUS
    return True


def build_reservation_view_invalidation_handler(channel: ViewInvalidationChannel):
    """`reservation_list` (org-wide) and `reservation_detail` (exact resource) are Reservation's
    own two projections -- the Reservations workspace's owner target, mirroring Requisition's
    (P29) exact shape. `reservation_open_count` is a third, narrower org-wide target reserved for
    Dashboard's own "Open Reservations" KPI -- not a generic "Reservation changed" fan-out,
    computed precisely from the same open-membership predicate the KPI query itself uses (see
    `_reservation_event_notifies_open_count`), the established convention Requisition's own
    `requisition_pending_approval` target already set (P29) for a capability summary narrower
    than either list or detail.

    Deduplicated per (transaction correlation_id, target identity), matching every other
    Inventory/Procurement handler (P18B-FIX)."""

    current_correlation_id: list[str | None] = [None]
    notified_list_targets: set[_ReservationOrgTarget] = set()
    notified_detail_targets: set[_ReservationDetailTarget] = set()
    notified_open_count_targets: set[_ReservationOrgTarget] = set()

    def handle_reservation_event(
        event: _ReservationEvent,
        context: DomainEventContext,
    ) -> None:
        if context.correlation_id != current_correlation_id[0]:
            current_correlation_id[0] = context.correlation_id
            notified_list_targets.clear()
            notified_detail_targets.clear()
            notified_open_count_targets.clear()

        org_scope = OrganizationScope(event.tenant_id, event.organization_id)

        list_target = (RESERVATION_LIST_SCOPE_CODE, event.tenant_id, event.organization_id)
        if list_target not in notified_list_targets:
            notified_list_targets.add(list_target)
            channel.notify(
                ViewInvalidationHint(
                    scope=org_scope,
                    category=RESERVATION_CATEGORY,
                    scope_code=RESERVATION_LIST_SCOPE_CODE,
                    entity_type=RESERVATION_ENTITY_TYPE,
                    entity_id=event.reservation_id,
                )
            )

        if _reservation_event_notifies_detail(event):
            detail_scope = ResourceScope(
                tenant_id=event.tenant_id,
                organization_id=event.organization_id,
                module_code=RESERVATION_MODULE_CODE,
                entity_type=RESERVATION_ENTITY_TYPE,
                entity_id=event.reservation_id,
            )
            detail_target = (
                RESERVATION_DETAIL_SCOPE_CODE,
                event.tenant_id,
                event.organization_id,
                RESERVATION_MODULE_CODE,
                RESERVATION_ENTITY_TYPE,
                event.reservation_id,
            )
            if detail_target not in notified_detail_targets:
                notified_detail_targets.add(detail_target)
                channel.notify(
                    ViewInvalidationHint(
                        scope=detail_scope,
                        category=RESERVATION_CATEGORY,
                        scope_code=RESERVATION_DETAIL_SCOPE_CODE,
                        entity_type=RESERVATION_ENTITY_TYPE,
                        entity_id=event.reservation_id,
                    )
                )

        if _reservation_event_notifies_open_count(event):
            open_count_target = (
                RESERVATION_OPEN_COUNT_SCOPE_CODE,
                event.tenant_id,
                event.organization_id,
            )
            if open_count_target not in notified_open_count_targets:
                notified_open_count_targets.add(open_count_target)
                channel.notify(
                    ViewInvalidationHint(
                        scope=org_scope,
                        category=RESERVATION_CATEGORY,
                        scope_code=RESERVATION_OPEN_COUNT_SCOPE_CODE,
                        entity_type=RESERVATION_ENTITY_TYPE,
                        entity_id=event.reservation_id,
                    )
                )

    return handle_reservation_event


__all__ = [
    "build_storeroom_list_view_invalidation_handler",
    "build_location_list_view_invalidation_handler",
    "build_reorder_policy_list_view_invalidation_handler",
    "build_reservation_view_invalidation_handler",
    "INVENTORY_CATEGORY",
    "STOREROOM_LIST_SCOPE_CODE",
    "LOCATION_LIST_SCOPE_CODE",
    "REORDER_POLICY_LIST_SCOPE_CODE",
    "RESERVATION_CATEGORY",
    "RESERVATION_MODULE_CODE",
    "RESERVATION_ENTITY_TYPE",
    "RESERVATION_LIST_SCOPE_CODE",
    "RESERVATION_DETAIL_SCOPE_CODE",
    "RESERVATION_OPEN_COUNT_SCOPE_CODE",
]
