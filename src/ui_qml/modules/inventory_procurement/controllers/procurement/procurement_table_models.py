from __future__ import annotations

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


def create_procurement_table_models(
    parent,
) -> tuple[
    DynamicTableModel,
    DynamicTableModel,
    DynamicTableModel,
    DynamicTableModel,
    DynamicTableModel,
]:
    return (
        DynamicTableModel(parent),  # requisitions
        DynamicTableModel(parent),  # purchase_orders
        DynamicTableModel(parent),  # requisition_lines
        DynamicTableModel(parent),  # purchase_order_lines
        DynamicTableModel(parent),  # receipts
    )
