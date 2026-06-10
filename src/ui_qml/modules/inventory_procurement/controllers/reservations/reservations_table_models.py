from __future__ import annotations

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


def create_reservations_table_models(parent) -> DynamicTableModel:
    return DynamicTableModel(parent)
