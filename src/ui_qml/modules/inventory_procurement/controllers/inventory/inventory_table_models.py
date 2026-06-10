from __future__ import annotations

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


def create_inventory_table_models(
    parent,
) -> tuple[DynamicTableModel, DynamicTableModel, DynamicTableModel, DynamicTableModel]:
    return (
        DynamicTableModel(parent),  # storerooms
        DynamicTableModel(parent),  # balances
        DynamicTableModel(parent),  # transactions
        DynamicTableModel(parent),  # foundation
    )
