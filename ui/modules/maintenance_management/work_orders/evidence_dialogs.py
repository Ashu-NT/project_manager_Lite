from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.modules.maintenance_management import MaintenanceDocumentService
from src.core.platform.documents import DocumentStructure, DocumentType
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceWorkOrderEvidenceCaptureDialog(QDialog):
    def __init__(
        self,
        *,
        document_service: MaintenanceDocumentService,
        context_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document_service = document_service
        self._attachments: list[str] = []
        self.setWindowTitle("Capture Work Order Evidence")
        self.resize(620, 320)

        self.type_combo = QComboBox()
        for document_type in DocumentType:
            self.type_combo.addItem(document_type.value.replace("_", " ").title(), document_type)
        self.structure_combo = QComboBox()
        self.structure_combo.addItem("No structure", None)
        self.link_role_edit = QLineEdit("evidence")
        self.version_edit = QLineEdit()
        self.source_system_edit = QLineEdit("maintenance_execution")
        self.attachment_summary = QLineEdit()
        self.attachment_summary.setReadOnly(True)
        self.attachment_summary.setPlaceholderText("Choose one or more evidence files")
        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(80)
        self.notes_edit.setPlaceholderText("Optional execution notes for the captured evidence.")
        self.btn_browse = QPushButton("Browse Files...")
        self.btn_browse.setFixedHeight(CFG.BUTTON_HEIGHT)

        info = QLabel(f"Capture new shared-document evidence for {context_label}.")
        info.setWordWrap(True)
        info.setStyleSheet(CFG.NOTE_STYLE_SHEET)

        attachment_row = QHBoxLayout()
        attachment_row.setSpacing(CFG.SPACING_SM)
        attachment_row.addWidget(self.attachment_summary, 1)
        attachment_row.addWidget(self.btn_browse)

        form = QFormLayout()
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.addRow("Files", attachment_row)
        form.addRow("Document type", self.type_combo)
        form.addRow("Structure", self.structure_combo)
        form.addRow("Link role", self.link_role_edit)
        form.addRow("Version / revision", self.version_edit)
        form.addRow("Source system", self.source_system_edit)
        form.addRow("Notes", self.notes_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        self.btn_browse.clicked.connect(self._browse_for_files)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addWidget(info)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._reload_structures()

    @property
    def attachments(self) -> list[str]:
        return list(self._attachments)

    @property
    def document_type(self) -> DocumentType:
        return self.type_combo.currentData() or DocumentType.GENERAL

    @property
    def document_structure_id(self) -> str | None:
        value = self.structure_combo.currentData()
        normalized = str(value or "").strip()
        return normalized or None

    @property
    def link_role(self) -> str:
        return self.link_role_edit.text().strip() or "evidence"

    @property
    def business_version_label(self) -> str:
        return self.version_edit.text().strip()

    @property
    def source_system(self) -> str:
        return self.source_system_edit.text().strip() or "maintenance_execution"

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    def _reload_structures(self) -> None:
        try:
            rows = self._document_service.list_document_structures(active_only=True)
        except Exception:  # noqa: BLE001
            rows = []
        for structure in rows:
            self.structure_combo.addItem(
                f"{structure.structure_code} - {structure.name}",
                structure.id,
            )

    def _browse_for_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select evidence files",
            "",
            "Documents (*.pdf *.doc *.docx *.xls *.xlsx *.ppt *.pptx *.png *.jpg *.jpeg *.txt);;All files (*.*)",
        )
        if not paths:
            return
        self._attachments = list(paths)
        if len(paths) == 1:
            self.attachment_summary.setText(paths[0])
        else:
            self.attachment_summary.setText(f"{len(paths)} files selected")

    def _accept_if_valid(self) -> None:
        if not self._attachments:
            QMessageBox.warning(self, "Capture Work Order Evidence", "Select at least one evidence file.")
            return
        self.accept()


class MaintenanceWorkOrderEvidenceLinkDialog(QDialog):
    def __init__(
        self,
        *,
        document_service: MaintenanceDocumentService,
        context_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._document_service = document_service
        self.setWindowTitle("Link Existing Evidence")
        self.resize(560, 220)

        self.document_combo = QComboBox()
        self.link_role_edit = QLineEdit("evidence")
        self.summary_label = QLabel(f"Link an existing shared document into {context_label}.")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)

        form = QFormLayout()
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.addRow("Document", self.document_combo)
        form.addRow("Link role", self.link_role_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addWidget(self.summary_label)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._reload_documents()

    @property
    def document_id(self) -> str | None:
        value = self.document_combo.currentData()
        normalized = str(value or "").strip()
        return normalized or None

    @property
    def link_role(self) -> str:
        return self.link_role_edit.text().strip() or "evidence"

    def _reload_documents(self) -> None:
        try:
            rows = self._document_service.list_available_documents(active_only=True)
        except Exception:  # noqa: BLE001
            rows = []
        self.document_combo.clear()
        self.document_combo.addItem("Select document", None)
        for document in rows:
            self.document_combo.addItem(
                f"{document.document_code} - {document.title}",
                document.id,
            )

    def _accept_if_valid(self) -> None:
        if not self.document_id:
            QMessageBox.warning(self, "Link Existing Evidence", "Please select a document to link.")
            return
        self.accept()


__all__ = [
    "MaintenanceWorkOrderEvidenceCaptureDialog",
    "MaintenanceWorkOrderEvidenceLinkDialog",
]
