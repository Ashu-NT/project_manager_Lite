from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject

from src.ui_qml.shared.models.data_table_model import DynamicTableModel


@dataclass
class PortfolioTableModels:
    heatmap: DynamicTableModel
    intake_items: DynamicTableModel
    dependencies: DynamicTableModel


def create_portfolio_table_models(parent: QObject) -> PortfolioTableModels:
    return PortfolioTableModels(
        heatmap=DynamicTableModel(parent),
        intake_items=DynamicTableModel(parent),
        dependencies=DynamicTableModel(parent),
    )


__all__ = ["PortfolioTableModels", "create_portfolio_table_models"]
