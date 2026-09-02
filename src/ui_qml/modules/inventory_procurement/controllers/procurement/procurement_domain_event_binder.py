from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_domain_events(ctrl) -> None:
    """P7A: direct-wired to the specific legacy signals this workspace actually reads -- no
    generic `domain_changed` bridge. `inventory_items_changed`/`inventory_item_categories_changed`
    removed (P24): the `item_options` selector is a real Item dependency, now served by
    `InventoryCatalogViewInvalidationAdapter.itemListStale` wired to the narrow
    `refresh_item_options()` seam in context.py; Category has zero dependency here
    (source-proven), so no replacement subscription for it."""

    def _on_domain_event(_payload: object) -> None:
        ctrl._request_domain_refresh()

    for signal in (
        domain_events.inventory_balances_changed,
        domain_events.inventory_reservations_changed,
        domain_events.inventory_requisitions_changed,
        domain_events.inventory_purchase_orders_changed,
        domain_events.inventory_receipts_changed,
        domain_events.inventory_reorder_policies_changed,
        domain_events.inventory_cycle_counts_changed,
    ):
        ctrl._subscribe_domain_signal(signal, _on_domain_event)
