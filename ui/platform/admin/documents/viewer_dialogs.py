from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.platform.documents import Document, DocumentLink
from ui.platform.admin.documents.preview import DocumentPreviewWidget
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class DocumentPreviewDialog(QDialog):
    def __init__(self, document: Document, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Document Preview - {document.document_code}")
        self.resize(960, 720)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.preview_widget = DocumentPreviewWidget(self)
        self.preview_widget.set_document(document)
        layout.addWidget(self.preview_widget, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.button(QDialogButtonBox.Close).clicked.connect(self.close)
        layout.addWidget(buttons)


class DocumentLinksDialog(QDialog):
    def __init__(
        self,
        *,
        document: Document,
        links: list[DocumentLink],
        selection_mode: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self._links = list(links)
        self._selection_mode = selection_mode
        self.setWindowTitle(f"Linked Records - {document.document_code}")
        self.resize(760, 420)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        summary = QLabel(
            "This shared document can be linked to records across project, maintenance, inventory, QHSE, and HR workflows."
        )
        summary.setWordWrap(True)
        summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(summary)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Module", "Entity Type", "Entity Id", "Role"])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.table, 1)

        self.empty_label = QLabel("No linked records yet.")
        self.empty_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.empty_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.empty_label)

        buttons = QDialogButtonBox()
        if self._selection_mode:
            self.select_button = buttons.addButton("Select Link", QDialogButtonBox.AcceptRole)
            self.select_button.clicked.connect(self._accept_selected)
        else:
            self.select_button = None
        close_label = "Cancel" if self._selection_mode else "Close"
        close_role = QDialogButtonBox.RejectRole if self._selection_mode else QDialogButtonBox.AcceptRole
        self.close_button = buttons.addButton(close_label, close_role)
        self.close_button.clicked.connect(self.reject if self._selection_mode else self.accept)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        self.table.setRowCount(len(self._links))
        for row, link in enumerate(self._links):
            for col, value in enumerate((link.module_code, link.entity_type, link.entity_id, link.link_role or "-")):
                self.table.setItem(row, col, QTableWidgetItem(value))
            self.table.item(row, 0).setData(Qt.UserRole, link.id)
        if self._links:
            self.table.selectRow(0)
        self.empty_label.setVisible(not self._links)
        if self.select_button is not None:
            self.select_button.setEnabled(bool(self._links))

    def _accept_selected(self) -> None:
        if self.selected_link is None:
            return
        self.accept()

    @property
    def selected_link(self) -> DocumentLink | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        selected_id = item.data(Qt.UserRole)
        for link in self._links:
            if link.id == selected_id:
                return link
        return None


__all__ = ["DocumentLinksDialog", "DocumentPreviewDialog"]
