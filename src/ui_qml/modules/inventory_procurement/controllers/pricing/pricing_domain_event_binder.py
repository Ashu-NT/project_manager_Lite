from __future__ import annotations


def bind_domain_events(ctrl) -> None:
    """P33: `inventory_receipts_changed` deleted -- Pricing's genuine Receipt dependency (its own
    "Receipts" metric count) is now covered by the typed `ReceiptViewInvalidationAdapter` wired
    in `context.py`, not this legacy binder."""
