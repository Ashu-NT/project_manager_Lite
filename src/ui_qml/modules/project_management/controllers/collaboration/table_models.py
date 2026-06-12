from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


@dataclass
class CollaborationTableModels:
    inbox: DynamicTableModel
    mentions: DynamicTableModel
    approvals: DynamicTableModel
    team_updates: DynamicTableModel
    related_items: DynamicTableModel


def create_collaboration_table_models(parent: QObject) -> CollaborationTableModels:
    return CollaborationTableModels(
        inbox=DynamicTableModel(parent),
        mentions=DynamicTableModel(parent),
        approvals=DynamicTableModel(parent),
        team_updates=DynamicTableModel(parent),
        related_items=DynamicTableModel(parent),
    )


__all__ = ["CollaborationTableModels", "create_collaboration_table_models"]
