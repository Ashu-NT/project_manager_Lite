from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from src.api.desktop.platform import DocumentDto, DocumentStructureDto
from src.core.platform.documents import DocumentStorageKind, DocumentType
from src.ui.shared.widgets.code_generation import CodeFieldWidget
from src.ui.shared.formatting.ui_config import UIConfig as CFG

_CONFIDENTIALITY_LEVELS = ["", "PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"]


class DocumentEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        document: DocumentDto | None = None,
        structures: list[DocumentStructureDto] | None = None,
    ):
        super().__init__(parent)
        self._structures = list(structures or [])
        self.setWindowTitle("Document" + (" - Edit" if document else " - New"))

        self.document_code_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.document_code_field = CodeFieldWidget(
            prefix="DOC",
            line_edit=self.document_code_edit,
            hint_getters=(lambda: self.title_edit.text(), lambda: self.file_name_edit.text()),
        )
        self.storage_uri_edit = QLineEdit()
        self.storage_uri_browse_button = QPushButton("Browse...")
        self.file_name_edit = QLineEdit()
        self.revision_edit = QLineEdit()
        self.source_system_edit = QLineEdit()
        self.structure_combo = QComboBox()
        for edit in (
            self.document_code_edit,
            self.title_edit,
            self.storage_uri_edit,
            self.file_name_edit,
            self.revision_edit,
            self.source_system_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        self.storage_uri_browse_button.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.storage_uri_browse_button.setMinimumWidth(CFG.BUTTON_MIN_WIDTH_SM)
        self.structure_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.structure_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.structure_combo.addItem("No structure", userData="")
        for structure in self._structures:
            self.structure_combo.addItem(
                f"{structure.structure_code} - {structure.name}",
                userData=structure.id,
            )

        self.document_type_combo = QComboBox()
        for document_type in DocumentType:
            self.document_type_combo.addItem(document_type.value.replace("_", " ").title(), userData=document_type)
        self.document_type_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.document_type_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.storage_kind_combo = QComboBox()
        for storage_kind in DocumentStorageKind:
            self.storage_kind_combo.addItem(storage_kind.value.replace("_", " ").title(), userData=storage_kind)
        self.storage_kind_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.storage_kind_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.confidentiality_combo = QComboBox()
        for level in _CONFIDENTIALITY_LEVELS:
            label = level.title() if level else "Not set"
            self.confidentiality_combo.addItem(label, userData=level)
        self.confidentiality_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.confidentiality_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(90)
        self.notes_edit.setPlaceholderText("Optional notes, revision hints, or usage context.")

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if document is not None:
            self.document_code_edit.setText(document.document_code)
            self.title_edit.setText(document.title)
            self.storage_uri_edit.setText(document.storage_uri)
            self.file_name_edit.setText(document.file_name)
            self.revision_edit.setText(document.business_version_label)
            self.source_system_edit.setText(document.source_system)
            self.notes_edit.setPlainText(document.notes or "")
            self.active_check.setChecked(document.is_active)
            self._select_combo(self.document_type_combo, document.document_type)
            self._select_combo(self.storage_kind_combo, document.storage_kind)
            self._select_combo(self.confidentiality_combo, document.confidentiality_level)
            self._select_combo(self.structure_combo, document.document_structure_id or "")
        else:
            self.active_check.setChecked(True)
            self.source_system_edit.setText("platform")

        self.storage_uri_edit.setPlaceholderText("Local file path, web URL, or enterprise reference...")
        self.file_name_edit.setPlaceholderText("Optional override. Defaults from the selected path or URL.")
        self.revision_edit.setPlaceholderText("R1, Rev A, 2026.03 ...")
        self.source_system_edit.setPlaceholderText("platform, sharepoint, dms, maintenance ...")

        storage_uri_row = QHBoxLayout()
        storage_uri_row.setSpacing(CFG.SPACING_SM)
        storage_uri_row.addWidget(self.storage_uri_edit, 1)
        storage_uri_row.addWidget(self.storage_uri_browse_button)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Document code:", self.document_code_field)
        form.addRow("Title:", self.title_edit)
        form.addRow("Document type:", self.document_type_combo)
        form.addRow("Document structure:", self.structure_combo)
        form.addRow("Storage kind:", self.storage_kind_combo)
        form.addRow("Storage URI:", storage_uri_row)
        form.addRow("File name:", self.file_name_edit)
        form.addRow("Version / revision:", self.revision_edit)
        form.addRow("Source system:", self.source_system_edit)
        form.addRow("Confidentiality:", self.confidentiality_combo)
        form.addRow("Notes:", self.notes_edit)
        form.addRow("", self.active_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        self.storage_uri_browse_button.clicked.connect(self._browse_for_file)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.resize(max(self.width(), 520), max(self.height(), 360))

    def _browse_for_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select document",
            "",
            "Documents (*.pdf *.doc *.docx *.xls *.xlsx *.ppt *.pptx *.png *.jpg *.jpeg *.txt);;All files (*.*)",
        )
        if not path:
            return
        self.storage_kind_combo.setCurrentIndex(self.storage_kind_combo.findData(DocumentStorageKind.FILE_PATH))
        self.storage_uri_edit.setText(path)
        if not self.file_name_edit.text().strip():
            normalized = path.replace("\\", "/").split("/")[-1]
            self.file_name_edit.setText(normalized)

    def _select_combo(self, combo: QComboBox, value) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                break

    def _validate_and_accept(self) -> None:
        if not self.document_code:
            QMessageBox.warning(self, "Document", "Document code is required.")
            return
        if not self.title:
            QMessageBox.warning(self, "Document", "Document title is required.")
            return
        if not self.storage_uri:
            QMessageBox.warning(self, "Document", "Document storage URI is required.")
            return
        self.accept()

    @property
    def document_code(self) -> str:
        return self.document_code_edit.text().strip().upper()

    @property
    def title(self) -> str:
        return self.title_edit.text().strip()

    @property
    def document_type(self) -> DocumentType:
        return self.document_type_combo.currentData() or DocumentType.GENERAL

    @property
    def classification(self) -> DocumentType:
        return self.document_type

    @property
    def document_structure_id(self) -> str | None:
        value = self.structure_combo.currentData()
        normalized = str(value or "").strip()
        return normalized or None

    @property
    def storage_kind(self) -> DocumentStorageKind:
        return self.storage_kind_combo.currentData() or DocumentStorageKind.FILE_PATH

    @property
    def storage_uri(self) -> str:
        return self.storage_uri_edit.text().strip()

    @property
    def storage_ref(self) -> str:
        return self.storage_uri

    @property
    def file_name(self) -> str:
        return self.file_name_edit.text().strip()

    @property
    def business_version_label(self) -> str:
        return self.revision_edit.text().strip()

    @property
    def revision(self) -> str:
        return self.business_version_label

    @property
    def source_system(self) -> str:
        return self.source_system_edit.text().strip()

    @property
    def confidentiality_level(self) -> str:
        return self.confidentiality_combo.currentData() or ""

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


class DocumentLinkEditDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Link Document")

        self.module_code_edit = QLineEdit()
        self.entity_type_edit = QLineEdit()
        self.entity_id_edit = QLineEdit()
        self.link_role_edit = QLineEdit()
        for edit in (self.module_code_edit, self.entity_type_edit, self.entity_id_edit, self.link_role_edit):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        self.module_code_edit.setPlaceholderText("project_management, maintenance_management, qhse, hr_management ...")
        self.entity_type_edit.setPlaceholderText("task, asset, employee, inspection, report ...")
        self.entity_id_edit.setPlaceholderText("Business object identifier")
        self.link_role_edit.setPlaceholderText("reference, attachment, evidence, certificate ...")

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Module code:", self.module_code_edit)
        form.addRow("Entity type:", self.entity_type_edit)
        form.addRow("Entity id:", self.entity_id_edit)
        form.addRow("Link role:", self.link_role_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self.module_code:
            QMessageBox.warning(self, "Document Link", "Module code is required.")
            return
        if not self.entity_type:
            QMessageBox.warning(self, "Document Link", "Entity type is required.")
            return
        if not self.entity_id:
            QMessageBox.warning(self, "Document Link", "Entity id is required.")
            return
        self.accept()

    @property
    def module_code(self) -> str:
        return self.module_code_edit.text().strip().lower()

    @property
    def entity_type(self) -> str:
        return self.entity_type_edit.text().strip()

    @property
    def entity_id(self) -> str:
        return self.entity_id_edit.text().strip()

    @property
    def link_role(self) -> str:
        return self.link_role_edit.text().strip()


__all__ = ["DocumentEditDialog", "DocumentLinkEditDialog"]
