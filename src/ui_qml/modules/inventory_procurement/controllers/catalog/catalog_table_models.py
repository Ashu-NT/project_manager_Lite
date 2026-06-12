from __future__ import annotations

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


def create_catalog_table_models(
    parent,
) -> tuple[DynamicTableModel, DynamicTableModel]:
    return DynamicTableModel(parent), DynamicTableModel(parent)
