from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from ui.styles.theme import table_stylesheet


def style_table(table: QTableView) -> None:
    """Apply consistent, professional table behavior and look."""
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setWordWrap(False)
    table.setMouseTracking(True)

    vh = table.verticalHeader()
    vh.setVisible(False)
    vh.setDefaultSectionSize(table.fontMetrics().height() + 10)

    hh = table.horizontalHeader()
    hh.setHighlightSections(False)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    # Keep sizing decisions in each tab/dialog; only apply shared visual style here.
    table.setStyleSheet(table_stylesheet())
