from __future__ import annotations


def bind_domain_events(ctrl) -> None:
    """P33: `inventory_receipts_changed` deleted -- Inventory(Foundation)'s genuine Receipt
    dependency (lot/serial/expiry tracking-signal panel) is now covered by the typed
    `ReceiptViewInvalidationAdapter` wired in `context.py`, not this legacy binder."""
