from __future__ import annotations


def bind_domain_events(ctrl) -> None:
    """P33: `inventory_receipts_changed` deleted -- Procurement's genuine Receipt dependency
    (receipt history embedded in PO detail, org-wide receipt count) is now covered by the typed
    `ReceiptViewInvalidationAdapter` wired in `context.py`, not this legacy binder."""
