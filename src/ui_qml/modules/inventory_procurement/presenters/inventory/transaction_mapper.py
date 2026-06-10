from __future__ import annotations

from src.ui_qml.modules.inventory_procurement.view_models.catalog import (
    InventoryRecordViewModel,
)


def to_transaction_record_view_model(transaction) -> InventoryRecordViewModel:
    return InventoryRecordViewModel(
        id=transaction.id,
        title=transaction.transaction_number,
        status_label=transaction.transaction_type_label,
        subtitle=f"{transaction.stock_item_label} @ {transaction.storeroom_label}",
        supporting_text=(
            f"{transaction.quantity_label} {transaction.uom or ''} | {transaction.transaction_at_label}"
        ).strip(),
        meta_text=(
            f"Ref {transaction.reference_type or '-'} / {transaction.reference_id or '-'} | {transaction.performed_by_username or '-'}"
        ),
        can_primary_action=False,
        can_secondary_action=False,
        can_tertiary_action=False,
        state={"transactionId": transaction.id},
    )
