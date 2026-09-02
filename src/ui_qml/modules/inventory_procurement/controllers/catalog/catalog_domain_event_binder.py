from __future__ import annotations


def bind_domain_events(ctrl) -> None:
    """P33: `inventory_receipts_changed` deleted -- Catalog has zero remaining legacy Inventory
    signals to subscribe to (confirmed incidental to Receipt since P32A/P33's own audit)."""
