from __future__ import annotations

from dataclasses import dataclass

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


@dataclass
class RegisterTableModels:
    entries: DynamicTableModel


def create_register_table_models(parent) -> RegisterTableModels:
    return RegisterTableModels(entries=DynamicTableModel(parent))


__all__ = ["RegisterTableModels", "create_register_table_models"]
