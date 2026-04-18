from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.documents import DocumentService, DocumentStructure, DocumentType
from ui.platform.shared.code_generation import CodeFieldWidget
from ui.platform.shared.styles.ui_config import UIConfig as CFG

_OBJECT_SCOPE_CHOICES = (
    "GENERAL",
    "ASSET",
    "SYSTEM",
    "WORK_ORDER",
    "TASK_TEMPLATE",
    "EMPLOYEE",
    "INSPECTION",
    "REPORT",
    "INVENTORY_ITEM",
    "STOREROOM",
    "SITE",
    "DEPARTMENT",
)


class DocumentStructureEditDialog(QDialog):
    def __init__(
        self,
        *,
        structures: list[DocumentStructure],
        structure: DocumentStructure | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._structures = list(structures)
        self._structure = structure
        self.setWindowTitle("Edit Document Structure" if structure is not None else "New Document Structure")
        self.resize(540, 420)
        self._setup_ui()
        self._load_structure()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Build the shared document taxonomy that project, maintenance, QHSE, HR, and inventory records can all reuse."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.structure_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.structure_code_field = CodeFieldWidget(
            prefix="DOCSTR",
            line_edit=self.structure_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.parent_combo = QComboBox()
        self.parent_combo.addItem("No parent", userData="")
        for candidate in self._structures:
            if self._structure is not None and candidate.id == self._structure.id:
                continue
            self.parent_combo.addItem(
                f"{candidate.structure_code} - {candidate.name}",
                userData=candidate.id,
            )
        self.object_scope_combo = QComboBox()
        self.object_scope_combo.setEditable(True)
        self.object_scope_combo.addItems(_OBJECT_SCOPE_CHOICES)
        self.default_document_type_combo = QComboBox()
        for document_type in DocumentType:
            self.default_document_type_combo.addItem(
                document_type.value.replace("_", " ").title(),
                userData=document_type,
            )
        self.sort_order_spin = QSpinBox()
        self.sort_order_spin.setRange(0, 9999)
        self.description_edit = QLineEdit()
        self.notes_edit = QLineEdit()
        self.is_active_check = QCheckBox("Active")

        form.addRow("Structure code", self.structure_code_field)
        form.addRow("Name", self.name_edit)
        form.addRow("Parent", self.parent_combo)
        form.addRow("Object scope", self.object_scope_combo)
        form.addRow("Default document type", self.default_document_type_combo)
        form.addRow("Sort order", self.sort_order_spin)
        form.addRow("Description", self.description_edit)
        form.addRow("Notes", self.notes_edit)
        form.addRow("Status", self.is_active_check)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_structure(self) -> None:
        structure = self._structure
        if structure is None:
            self.object_scope_combo.setCurrentText("GENERAL")
            self.default_document_type_combo.setCurrentIndex(
                self.default_document_type_combo.findData(DocumentType.GENERAL)
            )
            self.is_active_check.setChecked(True)
            return
        self.structure_code_edit.setText(structure.structure_code)
        self.name_edit.setText(structure.name)
        self.description_edit.setText(structure.description)
        self.notes_edit.setText(structure.notes)
        self.object_scope_combo.setCurrentText(structure.object_scope)
        self.sort_order_spin.setValue(structure.sort_order)
        self.is_active_check.setChecked(structure.is_active)
        self._select_combo(self.parent_combo, structure.parent_structure_id or "")
        self._select_combo(self.default_document_type_combo, structure.default_document_type)

    @staticmethod
    def _select_combo(combo: QComboBox, value) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                return

    @property
    def structure_code(self) -> str:
        return self.structure_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def parent_structure_id(self) -> str | None:
        value = str(self.parent_combo.currentData() or "").strip()
        return value or None

    @property
    def object_scope(self) -> str:
        return str(self.object_scope_combo.currentText()).strip()

    @property
    def default_document_type(self) -> DocumentType:
        return self.default_document_type_combo.currentData() or DocumentType.GENERAL

    @property
    def sort_order(self) -> int:
        return int(self.sort_order_spin.value())

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.text().strip()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


class DocumentStructureManagerDialog(QDialog):
    def __init__(self, *, document_service: DocumentService, parent=None) -> None:
        super().__init__(parent)
        self._document_service = document_service
        self._rows: list[DocumentStructure] = []
        self.setWindowTitle("Document Structures")
        self.resize(880, 520)
        self._setup_ui()
        self.reload_structures()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        intro = QLabel(
            "Manage the shared document taxonomy used to organize manuals, procedures, certificates, drawings, reports, and other controlled records."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        action_row = QHBoxLayout()
        self.btn_new = QPushButton("New Structure")
        self.btn_edit = QPushButton("Edit Structure")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        for button in (self.btn_new, self.btn_edit, self.btn_toggle_active, self.btn_refresh):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            action_row.addWidget(button)
        action_row.addStretch(1)
        root.addLayout(action_row)

        self.summary_label = QLabel("0 structures")
        self.summary_label.setWordWrap(True)
        root.addWidget(self.summary_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(("Code", "Name", "Scope", "Default Type", "Parent", "Active"))
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        close_button = buttons.button(QDialogButtonBox.Close)
        if close_button is not None:
            close_button.clicked.connect(self.accept)
        root.addWidget(buttons)

        self.btn_new.clicked.connect(self.create_structure)
        self.btn_edit.clicked.connect(self.edit_structure)
        self.btn_toggle_active.clicked.connect(self.toggle_active)
        self.btn_refresh.clicked.connect(self.reload_structures)
        self.table.itemSelectionChanged.connect(self._sync_actions)
        self._sync_actions()

    def reload_structures(self) -> None:
        try:
            self._rows = self._document_service.list_document_structures(active_only=None)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Document Structures", str(exc))
            self._rows = []
        except Exception as exc:
            QMessageBox.critical(self, "Document Structures", f"Failed to load document structures: {exc}")
            self._rows = []
        by_id = {row.id: row for row in self._rows}
        self.table.setRowCount(len(self._rows))
        for row_index, structure in enumerate(self._rows):
            parent = by_id.get(structure.parent_structure_id or "")
            values = (
                structure.structure_code,
                structure.name,
                structure.object_scope,
                structure.default_document_type.value.replace("_", " ").title(),
                f"{parent.structure_code} - {parent.name}" if parent is not None else "-",
                "Yes" if structure.is_active else "No",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 5:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_index, col, item)
            self.table.item(row_index, 0).setData(Qt.UserRole, structure.id)
        self.summary_label.setText(f"{len(self._rows)} structures")
        if self._rows and self.table.currentRow() < 0:
            self.table.selectRow(0)
        self._sync_actions()

    def create_structure(self) -> None:
        dialog = DocumentStructureEditDialog(structures=self._rows, parent=self)
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.create_document_structure(
                    structure_code=dialog.structure_code,
                    name=dialog.name,
                    description=dialog.description,
                    parent_structure_id=dialog.parent_structure_id,
                    object_scope=dialog.object_scope,
                    default_document_type=dialog.default_document_type,
                    sort_order=dialog.sort_order,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Document Structures", str(exc))
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Document Structures", f"Failed to create structure: {exc}")
                return
            break
        self.reload_structures()

    def edit_structure(self) -> None:
        structure = self._selected_structure()
        if structure is None:
            QMessageBox.information(self, "Document Structures", "Please select a structure.")
            return
        dialog = DocumentStructureEditDialog(structures=self._rows, structure=structure, parent=self)
        while True:
            if dialog.exec() != QDialog.Accepted:
                return
            try:
                self._document_service.update_document_structure(
                    structure.id,
                    structure_code=dialog.structure_code,
                    name=dialog.name,
                    description=dialog.description,
                    parent_structure_id=dialog.parent_structure_id or "",
                    object_scope=dialog.object_scope,
                    default_document_type=dialog.default_document_type,
                    sort_order=dialog.sort_order,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                    expected_version=structure.version,
                )
            except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
                QMessageBox.warning(self, "Document Structures", str(exc))
                if isinstance(exc, ConcurrencyError):
                    self.reload_structures()
                    return
                continue
            except Exception as exc:
                QMessageBox.critical(self, "Document Structures", f"Failed to update structure: {exc}")
                return
            break
        self.reload_structures()

    def toggle_active(self) -> None:
        structure = self._selected_structure()
        if structure is None:
            QMessageBox.information(self, "Document Structures", "Please select a structure.")
            return
        try:
            self._document_service.update_document_structure(
                structure.id,
                is_active=not structure.is_active,
                expected_version=structure.version,
            )
        except (ValidationError, NotFoundError, BusinessRuleError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Document Structures", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Document Structures", f"Failed to update structure: {exc}")
            return
        self.reload_structures()

    def _selected_structure(self) -> DocumentStructure | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        structure_id = str(item.data(Qt.UserRole) or "") if item is not None else ""
        for structure in self._rows:
            if structure.id == structure_id:
                return structure
        return None

    def _sync_actions(self) -> None:
        has_selection = self._selected_structure() is not None
        self.btn_edit.setEnabled(has_selection)
        self.btn_toggle_active.setEnabled(has_selection)


__all__ = ["DocumentStructureEditDialog", "DocumentStructureManagerDialog"]
