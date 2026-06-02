"""Enterprise-grade 2D table model for the shared DataTable QML component.

Exposes rows and columns as QML-bindable properties and provides rich model
roles so TableView delegates can use required-property bindings instead of
direct array lookups.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QByteArray,
    QModelIndex,
    Qt,
    Property,
    Signal,
    Slot,
)
from PySide6.QtQml import QmlElement

QML_IMPORT_NAME = "App.Models"
QML_IMPORT_MAJOR_VERSION = 1


def _safe_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def _safe_float(v: Any) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


@QmlElement
class DynamicTableModel(QAbstractTableModel):
    """Full QAbstractTableModel backing the shared enterprise DataTable.

    Handles missing keys, null values, dicts, progress objects (number or
    {value, label}), status strings, booleans, dates, and unknown types.
    """

    # ── Custom roles ──────────────────────────────────────────────────
    RawValueRole      = Qt.UserRole + 1
    RowDataRole       = Qt.UserRole + 2
    ColumnDataRole    = Qt.UserRole + 3
    RowIdRole         = Qt.UserRole + 4
    ColumnKeyRole     = Qt.UserRole + 5
    ColumnLabelRole   = Qt.UserRole + 6
    ColumnTypeRole    = Qt.UserRole + 7
    RowIndexRole      = Qt.UserRole + 8
    ColumnIndexRole   = Qt.UserRole + 9
    SortableRole      = Qt.UserRole + 10
    MinWidthRole      = Qt.UserRole + 11
    FlexRole          = Qt.UserRole + 12
    AlignRole         = Qt.UserRole + 13
    EditableRole      = Qt.UserRole + 14
    IsRequiredRole    = Qt.UserRole + 15
    ColumnVisibleRole = Qt.UserRole + 16
    StatusRole        = Qt.UserRole + 17   # row-level status string (for row tinting)
    MetadataRole      = Qt.UserRole + 18   # per-row metadata dict (for contextual actions)
    WidthRole         = Qt.UserRole + 19   # explicit column pixel width override

    # ── Notify signals (must be declared before Property uses them) ───
    rowsChanged      = Signal()
    columnsChanged   = Signal()
    rowCountChanged  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list = []
        self._columns: list = []
        self._vis_cols: list = []
        self._unsorted_rows: list = []
        self._sort_key: str = ""
        self._sort_ascending: bool = True

    # ── QAbstractTableModel interface ─────────────────────────────────

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        return 0 if parent.isValid() else len(self._vis_cols)

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            Qt.DisplayRole:           QByteArray(b"display"),
            self.RawValueRole:        QByteArray(b"rawValue"),
            self.RowDataRole:         QByteArray(b"rowData"),
            self.ColumnDataRole:      QByteArray(b"columnData"),
            self.RowIdRole:           QByteArray(b"rowId"),
            self.ColumnKeyRole:       QByteArray(b"columnKey"),
            self.ColumnLabelRole:     QByteArray(b"columnLabel"),
            self.ColumnTypeRole:      QByteArray(b"columnType"),
            self.RowIndexRole:        QByteArray(b"rowIndex"),
            self.ColumnIndexRole:     QByteArray(b"columnIndex"),
            self.SortableRole:        QByteArray(b"sortable"),
            self.MinWidthRole:        QByteArray(b"minWidth"),
            self.FlexRole:            QByteArray(b"flex"),
            self.AlignRole:           QByteArray(b"align"),
            self.EditableRole:        QByteArray(b"editable"),
            self.IsRequiredRole:      QByteArray(b"isRequired"),
            self.ColumnVisibleRole:   QByteArray(b"columnVisible"),
            self.StatusRole:          QByteArray(b"rowStatus"),
            self.MetadataRole:        QByteArray(b"rowMetadata"),
            self.WidthRole:           QByteArray(b"columnWidth"),
        }

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:  # type: ignore[override]
        if not index.isValid():
            return None
        r, c = index.row(), index.column()
        if r < 0 or r >= len(self._rows) or c < 0 or c >= len(self._vis_cols):
            return None

        row_dict = self._rows[r]
        if not isinstance(row_dict, dict):
            row_dict = {}
        col_def = self._vis_cols[c]
        if not isinstance(col_def, dict):
            col_def = {}

        key = col_def.get("key", "")
        raw = row_dict.get(key) if key else None

        if role == Qt.DisplayRole:
            return self._to_display(raw, col_def)
        if role == self.RawValueRole:
            return raw
        if role == self.RowDataRole:
            return dict(row_dict)
        if role == self.ColumnDataRole:
            return dict(col_def)
        if role == self.RowIdRole:
            rid = row_dict.get("id")
            return _safe_str(rid if rid is not None else r)
        if role == self.ColumnKeyRole:
            return _safe_str(key)
        if role == self.ColumnLabelRole:
            return _safe_str(col_def.get("label", key))
        if role == self.ColumnTypeRole:
            return self._resolve_type(col_def)
        if role == self.RowIndexRole:
            return r
        if role == self.ColumnIndexRole:
            return c
        if role == self.SortableRole:
            return col_def.get("sortable", True) is not False
        if role == self.MinWidthRole:
            return int(col_def.get("minWidth", 80))
        if role == self.FlexRole:
            v = col_def.get("flex", 1)
            return float(v) if v is not None else 1.0
        if role == self.AlignRole:
            return _safe_str(col_def.get("align", "left"))
        if role == self.EditableRole:
            return bool(col_def.get("editable", False))
        if role == self.IsRequiredRole:
            return bool(col_def.get("required", False))
        if role == self.ColumnVisibleRole:
            return col_def.get("visible", True) is not False
        if role == self.StatusRole:
            return _safe_str(row_dict.get("_status", row_dict.get("status", "")))
        if role == self.MetadataRole:
            meta = row_dict.get("_meta")
            return dict(meta) if isinstance(meta, dict) else {}
        if role == self.WidthRole:
            v = col_def.get("width")
            return int(v) if v is not None else 0
        return None

    # ── QML-bindable properties ───────────────────────────────────────

    def _get_rows(self) -> list:
        return self._rows

    def _set_rows(self, value) -> None:
        next_rows = list(value) if value is not None else []
        if next_rows == self._rows:
            return
        self.beginResetModel()
        self._rows = next_rows
        self.endResetModel()
        self.rowsChanged.emit()
        self.rowCountChanged.emit()

    def _get_columns(self) -> list:
        return self._columns

    def _set_columns(self, value) -> None:
        next_columns = list(value) if value is not None else []
        if next_columns == self._columns:
            return
        next_vis_cols = [
            c for c in next_columns
            if isinstance(c, dict) and c.get("visible", True) is not False
        ]
        self.beginResetModel()
        self._columns = next_columns
        self._vis_cols = next_vis_cols
        self.endResetModel()
        self.columnsChanged.emit()

    rows          = Property("QVariantList", _get_rows,    _set_rows,    notify=rowsChanged)
    columns       = Property("QVariantList", _get_columns, _set_columns, notify=columnsChanged)
    rowCountValue = Property(int, lambda self: len(self._rows), notify=rowCountChanged)

    # ── Public controller API ─────────────────────────────────────────

    def set_rows(self, rows: list[dict]) -> None:
        """Push a new row dataset from Python without crossing the QML bridge."""
        self._unsorted_rows = list(rows) if rows is not None else []
        if self._sort_key:
            self._set_rows(self._sorted(self._unsorted_rows))
        else:
            self._set_rows(self._unsorted_rows)

    @Slot(str)
    def toggleSort(self, key: str) -> None:
        """Called from QML onSortRequested — toggles sort direction then re-sorts in place."""
        if not key:
            return
        if self._sort_key == key:
            self._sort_ascending = not self._sort_ascending
        else:
            self._sort_key = key
            self._sort_ascending = True
        self._set_rows(self._sorted(self._unsorted_rows))

    def _sorted(self, rows: list[dict]) -> list[dict]:
        key = self._sort_key
        if not key or not rows:
            return rows
        asc = self._sort_ascending

        def _val(row: dict):
            v = row.get(key)
            if v is None:
                return (1, "")
            if isinstance(v, (int, float)):
                return (0, v)
            return (0, str(v).lower())

        try:
            return sorted(rows, key=_val, reverse=not asc)
        except Exception:
            return rows

    def set_columns(self, columns: list[dict]) -> None:
        """Push a new column definition list from Python."""
        self._set_columns(columns)

    def append_rows(self, rows: list[dict]) -> None:
        """Append rows without a full model reset — for pagination append / lazy loading."""
        if not rows:
            return
        first = len(self._rows)
        last = first + len(rows) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self._rows.extend(rows)
        self.endInsertRows()
        self.rowsChanged.emit()
        self.rowCountChanged.emit()

    @Slot(int, result=str)
    def rowId(self, row: int) -> str:
        """Return the id string for *row* — used by DataTable frozen checkbox column."""
        if 0 <= row < len(self._rows):
            row_dict = self._rows[row]
            if isinstance(row_dict, dict):
                rid = row_dict.get("id")
                return str(rid) if rid is not None else str(row)
        return str(row)

    # ── Private helpers ───────────────────────────────────────────────

    @staticmethod
    def _resolve_type(col_def: dict) -> str:
        """Determine column type from explicit type or key-name conventions."""
        col_type = col_def.get("type", "")
        if col_type:
            return _safe_str(col_type)
        key = _safe_str(col_def.get("key", ""))
        if key in ("statusLabel", "status") or "StatusLabel" in key:
            return "status"
        return "text"

    @staticmethod
    def _to_display(raw: Any, col_def: dict) -> str:
        """Convert a raw cell value to a display string."""
        if raw is None or raw == "":
            return ""
        col_type = col_def.get("type", "text")
        if col_type == "progress":
            if isinstance(raw, dict):
                return _safe_str(raw.get("label", ""))
            val = _safe_float(raw)
            return f"{val * 100:.0f}%"
        if isinstance(raw, bool):
            return "Yes" if raw else "No"
        return _safe_str(raw)
