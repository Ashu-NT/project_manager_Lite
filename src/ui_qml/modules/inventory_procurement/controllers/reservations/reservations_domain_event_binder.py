from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_domain_events(ctrl) -> None:
    """P7A: direct-wired to the specific legacy signals this workspace actually reads -- no
    generic `domain_changed` bridge."""

    def _on_domain_event(_payload: object) -> None:
        ctrl._request_domain_refresh()

    for signal in (
        domain_events.inventory_items_changed,
        domain_events.inventory_item_categories_changed,
        domain_events.inventory_storerooms_changed,
        domain_events.inventory_balances_changed,
        domain_events.inventory_reservations_changed,
        domain_events.inventory_requisitions_changed,
        domain_events.inventory_purchase_orders_changed,
        domain_events.inventory_receipts_changed,
        domain_events.inventory_locations_changed,
        domain_events.inventory_reorder_policies_changed,
        domain_events.inventory_cycle_counts_changed,
    ):
        ctrl._subscribe_domain_signal(signal, _on_domain_event)
