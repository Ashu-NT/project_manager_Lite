from __future__ import annotations

from src.core.shared.events.domain_events import domain_events


def bind_domain_events(ctrl) -> None:
    """P7A: direct-wired to the specific legacy signals this workspace actually reads -- no
    generic `domain_changed` bridge. `inventory_items_changed`/`inventory_item_categories_changed`
    removed (P24): source-proven zero dependency on Item or Category data anywhere in Pricing's
    own presenter/state builders (site/storeroom/supplier options only) -- removed with no
    replacement, the same class of finding as P18B's Control-workspace `resources_changed`
    removal."""

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
