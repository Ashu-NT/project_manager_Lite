from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
)

from core.platform.org.domain import Department, Site
from ui.platform.shared.code_generation import CodeFieldWidget
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class DepartmentEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        department: Department | None = None,
        *,
        sites: list[Site] | None = None,
        parent_departments: list[Department] | None = None,
        location_options: list[object] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Department" + (" - Edit" if department else " - New"))
        self._location_options = list(location_options or [])

        self.department_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.department_code_field = CodeFieldWidget(
            prefix="DEPT",
            line_edit=self.department_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.department_type_edit = QLineEdit()
        self.cost_center_code_edit = QLineEdit()
        self.cost_center_code_field = CodeFieldWidget(
            prefix="CC",
            line_edit=self.cost_center_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.description_edit = QLineEdit()
        for edit in (
            self.department_code_edit,
            self.name_edit,
            self.department_type_edit,
            self.cost_center_code_edit,
            self.description_edit,
        ):
            edit.setSizePolicy(CFG.INPUT_POLICY)
            edit.setFixedHeight(CFG.INPUT_HEIGHT)
            edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)

        self.site_combo = QComboBox()
        self.site_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.site_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.site_combo.addItem("No site", userData="")
        for site in sites or []:
            self.site_combo.addItem(f"{site.site_code} - {site.name}", userData=site.id)

        self.parent_combo = QComboBox()
        self.parent_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.parent_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.parent_combo.addItem("No parent", userData="")
        for row in parent_departments or []:
            if department is not None and row.id == department.id:
                continue
            self.parent_combo.addItem(f"{row.department_code} - {row.name}", userData=row.id)

        self.default_location_combo = QComboBox()
        self.default_location_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.default_location_combo.setFixedHeight(CFG.INPUT_HEIGHT)

        self.notes_edit = QTextEdit()
        self.notes_edit.setMinimumHeight(90)
        self.notes_edit.setPlaceholderText("Optional department notes, governance reminders, or scope details.")

        self.active_check = QCheckBox("Active")
        self.active_check.setSizePolicy(CFG.CHKBOX_FIXED_HEIGHT)

        if department is not None:
            self.department_code_edit.setText(department.department_code)
            self.name_edit.setText(department.name)
            self.department_type_edit.setText(department.department_type)
            self.cost_center_code_edit.setText(department.cost_center_code)
            self.description_edit.setText(department.description)
            self.notes_edit.setPlainText(department.notes or "")
            self.active_check.setChecked(department.is_active)
            self._select_combo(self.site_combo, department.site_id)
            self._select_combo(self.parent_combo, department.parent_department_id)
        else:
            self.active_check.setChecked(True)

        self._reload_location_options(
            site_id=department.site_id if department is not None else self.site_id,
            selected_location_id=(department.default_location_id if department is not None else None),
        )
        self.site_combo.currentIndexChanged.connect(self._on_site_changed)

        form = QFormLayout()
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.addRow("Department code:", self.department_code_field)
        form.addRow("Name:", self.name_edit)
        form.addRow("Site:", self.site_combo)
        form.addRow("Default location:", self.default_location_combo)
        form.addRow("Parent department:", self.parent_combo)
        form.addRow("Department type:", self.department_type_edit)
        form.addRow("Cost center:", self.cost_center_code_field)
        form.addRow("Description:", self.description_edit)
        form.addRow("Notes:", self.notes_edit)
        form.addRow("", self.active_check)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setMinimumSize(self.sizeHint())

    def _select_combo(self, combo: QComboBox, value) -> None:
        for index in range(combo.count()):
            if combo.itemData(index) == value:
                combo.setCurrentIndex(index)
                break

    def _validate_and_accept(self) -> None:
        if not self.department_code:
            QMessageBox.warning(self, "Department", "Department code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "Department", "Department name is required.")
            return
        self.accept()

    def _on_site_changed(self) -> None:
        current_location_id = self.default_location_id
        self._reload_location_options(site_id=self.site_id, selected_location_id=current_location_id)

    def _reload_location_options(
        self,
        *,
        site_id: str | None,
        selected_location_id: str | None,
    ) -> None:
        self.default_location_combo.blockSignals(True)
        self.default_location_combo.clear()
        self.default_location_combo.addItem("No default location", userData="")
        for row in self._location_options:
            if site_id and getattr(row, "site_id", None) != site_id:
                continue
            label = f"{getattr(row, 'location_code', '')} - {getattr(row, 'name', '')}".strip(" -")
            self.default_location_combo.addItem(label or getattr(row, "name", "Location"), userData=row.id)
        self._select_combo(self.default_location_combo, selected_location_id)
        self.default_location_combo.blockSignals(False)

    @property
    def department_code(self) -> str:
        return self.department_code_edit.text().strip().upper()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def display_name(self) -> str:
        return self.name

    @property
    def site_id(self) -> str | None:
        return self.site_combo.currentData()

    @property
    def parent_department_id(self) -> str | None:
        return self.parent_combo.currentData()

    @property
    def default_location_id(self) -> str | None:
        return self.default_location_combo.currentData()

    @property
    def department_type(self) -> str:
        return self.department_type_edit.text().strip()

    @property
    def cost_center_code(self) -> str:
        return self.cost_center_code_edit.text().strip().upper()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_active(self) -> bool:
        return self.active_check.isChecked()


__all__ = ["DepartmentEditDialog"]
