from __future__ import annotations

import weakref

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableView
from shiboken6 import isValid

from ui.styles.theme import table_stylesheet


def _is_qobject_alive(obj) -> bool:
    try:
        return obj is not None and isValid(obj)
    except RuntimeError:
        return False


def _fit_table_columns(table: QTableView) -> None:
    if not _is_qobject_alive(table):
        return

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
    table._pm_is_fitting = True
    try:
        for col in range(col_count):
            mode = header.sectionResizeMode(col)
            if mode == QHeaderView.Stretch:
                continue
            if mode != QHeaderView.Interactive:
                header.setSectionResizeMode(col, QHeaderView.Interactive)
            width = header.sectionSize(col)
            target = max(min_w, min(max_w, width + padding))
            header.resizeSection(col, target)
    finally:
        table._pm_is_fitting = False


def _schedule_table_fit(table: QTableView) -> None:
    if not _is_qobject_alive(table):
        return

    if getattr(table, "_pm_fit_pending", False):
        return

    table._pm_fit_pending = True
    table_ref = weakref.ref(table)

    def _run():
        tbl = table_ref()
        if not _is_qobject_alive(tbl):
            return
        tbl._pm_fit_pending = False
        _fit_table_columns(tbl)

    QTimer.singleShot(0, _run)


def _bind_auto_fit_signals(table: QTableView) -> None:
    if not _is_qobject_alive(table):
        return

    model = table.model()
    if model is None:
        return

    model_id = id(model)
    if getattr(table, "_pm_fit_model_id", None) == model_id:
        return
    table._pm_fit_model_id = model_id

    table_ref = weakref.ref(table)

    def _queue_fit(*_args) -> None:
        tbl = table_ref()
        if not _is_qobject_alive(tbl):
            return
        _schedule_table_fit(tbl)

    model.modelReset.connect(_queue_fit)
    model.layoutChanged.connect(_queue_fit)
    model.dataChanged.connect(_queue_fit)
    model.rowsInserted.connect(_queue_fit)
    model.rowsRemoved.connect(_queue_fit)
    model.columnsInserted.connect(_queue_fit)
    model.columnsRemoved.connect(_queue_fit)

    header = table.horizontalHeader()

    def _on_user_resize(*_args) -> None:
        if getattr(table, "_pm_is_fitting", False):
            return
        table._pm_manual_resize_seen = True

    header.sectionResized.connect(_on_user_resize)

    _schedule_table_fit(table)


def style_table(table: QTableView) -> None:
    """Apply consistent, professional table behavior and look."""
    table.setAlternatingRowColors(True)
    table.setShowGrid(True)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setWordWrap(False)
    table.setMouseTracking(True)
    table.setFocusPolicy(Qt.StrongFocus)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

    vh = table.verticalHeader()
    vh.setVisible(False)
    vh.setDefaultSectionSize(table.fontMetrics().height() + 14)

    hh = table.horizontalHeader()
    hh.setHighlightSections(False)
    hh.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    hh.setMinimumSectionSize(72)
    hh.setDefaultSectionSize(max(110, hh.defaultSectionSize()))
    hh.setStretchLastSection(True)

    table.setStyleSheet(table_stylesheet())
    _bind_auto_fit_signals(table)
