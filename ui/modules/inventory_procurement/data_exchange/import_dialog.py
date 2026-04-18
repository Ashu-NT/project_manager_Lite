from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.modules.inventory_procurement import InventoryDataExchangeService
from src.core.platform.importing import ImportPreview
from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG

_IMPORT_TYPES = {
    "Items": "items",
    "Storerooms": "storerooms",
}


class InventoryImportDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        data_exchange_service: InventoryDataExchangeService,
    ) -> None:
        super().__init__(parent)
        self._data_exchange_service = data_exchange_service
        self._mapping_combos: dict[str, QComboBox] = {}
        self._current_preview: ImportPreview | None = None
        self.setWindowTitle("Inventory Import Wizard")
        self.resize(980, 720)
        self._setup_ui()
        self._reload_mapping_fields()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        intro = QLabel(
            "Preview inventory CSV loads before commit, map source columns when needed, and import only the rows that validate."
        )
        intro.setStyleSheet(CFG.INFO_TEXT_STYLE)
        intro.setWordWrap(True)
        root.addWidget(intro)

        file_row = QGridLayout()
        self.type_combo = QComboBox()
        for label, value in _IMPORT_TYPES.items():
            self.type_combo.addItem(label, userData=value)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.btn_browse = QPushButton("Browse CSV")
        self.btn_preview = QPushButton("Preview Import")
        self.btn_import = QPushButton("Import Valid Rows")
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        for button in (self.btn_browse, self.btn_preview, self.btn_import, self.btn_close):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_import.setEnabled(False)
        file_row.addWidget(QLabel("Import type"), 0, 0)
        file_row.addWidget(self.type_combo, 0, 1)
        file_row.addWidget(QLabel("Source file"), 1, 0)
        file_row.addWidget(self.file_path_edit, 1, 1)
        file_row.addWidget(self.btn_browse, 1, 2)
        file_row.addWidget(self.btn_preview, 2, 1)
        file_row.addWidget(self.btn_import, 2, 2)
        root.addLayout(file_row)

        content = QHBoxLayout()
        content.setSpacing(CFG.SPACING_MD)
        root.addLayout(content, 1)

        self.mapping_group = QGroupBox("Column Mapping")
        self.mapping_group.setFont(CFG.GROUPBOX_TITLE_FONT)
        self.mapping_layout = QGridLayout(self.mapping_group)
        self.mapping_layout.setHorizontalSpacing(CFG.SPACING_MD)
        self.mapping_layout.setVerticalSpacing(CFG.SPACING_SM)
        mapping_scroll = QScrollArea()
        mapping_scroll.setWidgetResizable(True)
        mapping_scroll.setWidget(self.mapping_group)
        mapping_scroll.setMinimumWidth(320)
        content.addWidget(mapping_scroll, 2)

        right_col = QVBoxLayout()
        content.addLayout(right_col, 5)

        self.summary_label = QLabel("Choose a CSV file to start.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        right_col.addWidget(self.summary_label)

        self.preview_table = QTableWidget(0, 4)
        self.preview_table.setHorizontalHeaderLabels(["Line", "Status", "Action", "Message"])
        self.preview_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.preview_table.setSelectionMode(QTableWidget.SingleSelection)
        self.preview_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.preview_table)
        right_col.addWidget(self.preview_table, 1)

        actions = QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.btn_close)
        root.addLayout(actions)

        self.type_combo.currentIndexChanged.connect(self._reload_mapping_fields)
        self.btn_browse.clicked.connect(self._choose_file)
        self.btn_preview.clicked.connect(self.preview_import)
        self.btn_import.clicked.connect(self.execute_import)
        self.btn_close.clicked.connect(self.reject)

    def _entity_type(self) -> str:
        return str(self.type_combo.currentData() or "items")

    def _reload_mapping_fields(self) -> None:
        while self.mapping_layout.count():
            item = self.mapping_layout.takeAt(0)
            widget = item.widget() if item is not None else None
            if widget is not None:
                widget.deleteLater()
        self._mapping_combos.clear()
        schema = self._data_exchange_service.get_import_schema(self._entity_type())
        for index, field in enumerate(schema):
            label = QLabel(f"{field.label}{' *' if field.required else ''}")
            combo = QComboBox()
            combo.addItem("<Auto / Unmapped>", userData=None)
            combo.setMinimumHeight(CFG.INPUT_HEIGHT)
            self.mapping_layout.addWidget(label, index, 0)
            self.mapping_layout.addWidget(combo, index, 1)
            self._mapping_combos[field.key] = combo
        self._load_columns_into_mapping()

    def _load_columns_into_mapping(self) -> None:
        path = self._selected_path()
        columns = self._data_exchange_service.read_csv_columns(path) if path else []
        schema = self._data_exchange_service.get_import_schema(self._entity_type())
        for field in schema:
            combo = self._mapping_combos[field.key]
            combo.blockSignals(True)
            current = combo.currentData()
            combo.clear()
            combo.addItem("<Auto / Unmapped>", userData=None)
            for column in columns:
                combo.addItem(column, userData=column)
            preferred = current if current in columns else (field.key if field.key in columns else None)
            index = combo.findData(preferred)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def _mapping_payload(self) -> dict[str, str | None]:
        return {key: combo.currentData() for key, combo in self._mapping_combos.items()}

    def _selected_path(self) -> Path | None:
        text = self.file_path_edit.text().strip()
        return Path(text) if text else None

    def _choose_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose inventory import file",
            "",
            "CSV files (*.csv);;All files (*.*)",
        )
        if not file_path:
            return
        self.file_path_edit.setText(file_path)
        self._load_columns_into_mapping()
        self._current_preview = None
        self.btn_import.setEnabled(False)
        self.summary_label.setText("File selected. Review the mapping and run a preview.")
        self.preview_table.setRowCount(0)

    def preview_import(self) -> None:
        path = self._selected_path()
        if path is None:
            QMessageBox.information(self, "Inventory Import Wizard", "Choose a CSV file first.")
            return
        try:
            preview = self._data_exchange_service.preview_csv(
                self._entity_type(),
                path,
                column_mapping=self._mapping_payload(),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Inventory Import Wizard", str(exc))
            return
        self._current_preview = preview
        self._render_preview(preview)

    def _render_preview(self, preview: ImportPreview) -> None:
        self.summary_label.setText(
            f"{preview.ready_count} ready rows | "
            f"{preview.created_count} create | {preview.updated_count} update | {preview.error_count} errors"
        )
        self.preview_table.setRowCount(len(preview.rows))
        for row_index, row in enumerate(preview.rows):
            values = [str(row.line_no), row.status, row.action, row.message]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.preview_table.setItem(row_index, column, item)
        self.btn_import.setEnabled(preview.ready_count > 0)

    def execute_import(self) -> None:
        path = self._selected_path()
        if path is None:
            QMessageBox.information(self, "Inventory Import Wizard", "Choose a CSV file first.")
            return
        if self._current_preview is None:
            self.preview_import()
            if self._current_preview is None:
                return
        try:
            summary = self._data_exchange_service.import_csv(
                self._entity_type(),
                path,
                column_mapping=self._mapping_payload(),
            )
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Inventory Import Wizard", str(exc))
            return
        details = [
            f"Created: {summary.created_count}",
            f"Updated: {summary.updated_count}",
            f"Errors: {summary.error_count}",
        ]
        if summary.error_rows:
            details.append("")
            details.append("First errors:")
            details.extend(summary.error_rows[:8])
        QMessageBox.information(self, "Inventory Import Wizard", "\n".join(details))
        self.accept()


__all__ = ["InventoryImportDialog"]
