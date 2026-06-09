from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


@dataclass
class TimesheetsTableModels:
    entries: DynamicTableModel
    review_queue: DynamicTableModel


def create_timesheets_table_models(parent: QObject) -> TimesheetsTableModels:
    return TimesheetsTableModels(
        entries=DynamicTableModel(parent),
        review_queue=DynamicTableModel(parent),
    )


__all__ = ["TimesheetsTableModels", "create_timesheets_table_models"]
