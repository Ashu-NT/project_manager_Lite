from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView

from ui.styles.theme import table_stylesheet


def _fit_table_columns(table: QTableView) -> None:
    model = table.model()
    if model is None:
        return

    col_count = model.columnCount()
    if col_count <= 0:
        return

    table.resizeColumnsToContents()
    table.resizeRowsToContents()

    min_w = 84
    max_w = 460
    padding = 18
    header = table.horizontalHeader()
    for col in range(col_count):
        if header.sectionResizeMode(col) == QHeaderView.Stretch:
            continue
        width = header.sectionSize(col)
        target = max(min_w, min(max_w, width + padding))
        header.resizeSection(col, target)


def _schedule_table_fit(table: QTableView) -> None:
    if getattr(table, "_pm_fit_pending", False):
        return

    table._pm_fit_pending = True

    def _run():
        table._pm_fit_pending = False
        _fit_table_columns(table)

    QTimer.singleShot(0, _run)


def _bind_auto_fit_signals(table: QTableView) -> None:
    model = table.model()
    if model is None:
        return

    model_id = id(model)
    if getattr(table, "_pm_fit_model_id", None) == model_id:
        return
    table._pm_fit_model_id = model_id

    model.modelReset.connect(lambda: _schedule_table_fit(table))
    model.layoutChanged.connect(lambda: _schedule_table_fit(table))
    model.dataChanged.connect(lambda *_args: _schedule_table_fit(table))
    model.rowsInserted.connect(lambda *_args: _schedule_table_fit(table))
    model.rowsRemoved.connect(lambda *_args: _schedule_table_fit(table))
    model.columnsInserted.connect(lambda *_args: _schedule_table_fit(table))
    model.columnsRemoved.connect(lambda *_args: _schedule_table_fit(table))

    _schedule_table_fit(table)


def style_table(table: QTableView) -> None:
    """Apply consistent, professional table behavior and look."""
    table.setAlternatingRowColors(True)
    table.setShowGrid(True)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setWordWrap(False)
    table.setMouseTracking(True)
    table.setFocusPolicy(Qt.StrongFocus)

    vh = table.verticalHeader()
    vh.setVisible(False)
    vh.setDefaultSectionSize(table.fontMetrics().height() + 12)

    hh = table.horizontalHeader()
    hh.setHighlightSections(False)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    hh.setMinimumSectionSize(72)
    hh.setStretchLastSection(True)

    table.setStyleSheet(table_stylesheet())
    _bind_auto_fit_signals(table)
