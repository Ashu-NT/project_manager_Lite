from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from core.modules.maintenance_management.domain import MaintenanceTaskStepTemplate, MaintenanceTemplateStatus
from ui.platform.shared.code_generation import CodeFieldWidget


class MaintenanceTaskTemplateEditDialog(QDialog):
    def __init__(self, *, task_template=None, parent=None) -> None:
        super().__init__(parent)
        self._task_template = task_template
        self.setWindowTitle("Edit Task Template" if task_template is not None else "New Task Template")
        self.resize(620, 620)
        self._setup_ui()
        self._load_template()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Build reusable maintenance task templates for preventive, inspection, calibration, and corrective execution patterns."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.code_field = CodeFieldWidget(
            prefix="TT",
            line_edit=self.code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.maintenance_type_edit = QLineEdit()
        self.revision_spin = QSpinBox()
        self.revision_spin.setRange(1, 999)
        self.status_combo = QComboBox()
        for value in MaintenanceTemplateStatus:
            self.status_combo.addItem(value.value.title(), value.value)
        self.estimated_minutes_spin = QSpinBox()
        self.estimated_minutes_spin.setRange(0, 100000)
        self.estimated_minutes_spin.setSpecialValueText("Not set")
        self.required_skill_edit = QLineEdit()
        self.description_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional planning notes, permit expectations, or library guidance.")
        self.requires_shutdown_check = QCheckBox("Requires shutdown")
        self.requires_permit_check = QCheckBox("Requires permit")
        self.is_active_check = QCheckBox("Active")

        form.addRow("Template Code", self.code_field)
        form.addRow("Name", self.name_edit)
        form.addRow("Maintenance Type", self.maintenance_type_edit)
        form.addRow("Revision", self.revision_spin)
        form.addRow("Template Status", self.status_combo)
        form.addRow("Estimated Minutes", self.estimated_minutes_spin)
        form.addRow("Required Skill", self.required_skill_edit)
        form.addRow("Description", self.description_edit)
        form.addRow("Notes", self.notes_edit)
        form.addRow("", self.requires_shutdown_check)
        form.addRow("", self.requires_permit_check)
        form.addRow("", self.is_active_check)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_template(self) -> None:
        task_template = self._task_template
        if task_template is None:
            self.revision_spin.setValue(1)
            self.status_combo.setCurrentText(MaintenanceTemplateStatus.DRAFT.value.title())
            self.is_active_check.setChecked(True)
            return
        self.code_edit.setText(task_template.task_template_code)
        self.name_edit.setText(task_template.name)
        self.maintenance_type_edit.setText(task_template.maintenance_type)
        self.revision_spin.setValue(task_template.revision_no)
        self._set_combo_to_data(self.status_combo, task_template.template_status.value)
        self.estimated_minutes_spin.setValue(task_template.estimated_minutes or 0)
        self.required_skill_edit.setText(task_template.required_skill)
        self.description_edit.setText(task_template.description)
        self.notes_edit.setPlainText(task_template.notes)
        self.requires_shutdown_check.setChecked(task_template.requires_shutdown)
        self.requires_permit_check.setChecked(task_template.requires_permit)
        self.is_active_check.setChecked(task_template.is_active)

    def _validate_and_accept(self) -> None:
        if not self.task_template_code:
            QMessageBox.warning(self, "Task Template", "Task template code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "Task Template", "Task template name is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def task_template_code(self) -> str:
        return self.code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def maintenance_type(self) -> str:
        return self.maintenance_type_edit.text().strip()

    @property
    def revision_no(self) -> int:
        return int(self.revision_spin.value())

    @property
    def template_status(self) -> str:
        return str(self.status_combo.currentData() or "").strip().upper()

    @property
    def estimated_minutes(self) -> int | None:
        value = int(self.estimated_minutes_spin.value())
        return value or None

    @property
    def required_skill(self) -> str:
        return self.required_skill_edit.text().strip()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def requires_shutdown(self) -> bool:
        return self.requires_shutdown_check.isChecked()

    @property
    def requires_permit(self) -> bool:
        return self.requires_permit_check.isChecked()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


class MaintenanceTaskStepTemplateEditDialog(QDialog):
    def __init__(self, *, step_template: MaintenanceTaskStepTemplate | None = None, parent=None) -> None:
        super().__init__(parent)
        self._step_template = step_template
        self.setWindowTitle("Edit Step Template" if step_template is not None else "New Step Template")
        self.resize(660, 680)
        self._setup_ui()
        self._load_step_template()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Capture reusable execution steps, confirmation rules, and field evidence expectations for the selected maintenance task template."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.step_number_spin = QSpinBox()
        self.step_number_spin.setRange(1, 999)
        self.sort_order_spin = QSpinBox()
        self.sort_order_spin.setRange(0, 999)
        self.sort_order_spin.setSpecialValueText("Use step number")
        self.instruction_edit = QPlainTextEdit()
        self.instruction_edit.setPlaceholderText("Describe the technician action for this step.")
        self.instruction_edit.setFixedHeight(82)
        self.expected_result_edit = QPlainTextEdit()
        self.expected_result_edit.setPlaceholderText("Optional expected result or acceptance guidance.")
        self.expected_result_edit.setFixedHeight(72)
        self.hint_level_combo = QComboBox()
        self.hint_level_combo.setEditable(True)
        self.hint_level_combo.addItem("No hint level", "")
        for value in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            self.hint_level_combo.addItem(value.title(), value)
        self.hint_text_edit = QPlainTextEdit()
        self.hint_text_edit.setPlaceholderText("Optional hint text shown to technicians during execution.")
        self.hint_text_edit.setFixedHeight(72)
        self.measurement_unit_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional notes for authoring, permits, or special handling.")
        self.notes_edit.setFixedHeight(72)
        self.requires_confirmation_check = QCheckBox("Requires confirmation")
        self.requires_measurement_check = QCheckBox("Requires measurement")
        self.requires_photo_check = QCheckBox("Requires photo")
        self.is_active_check = QCheckBox("Active")

        form.addRow("Step Number", self.step_number_spin)
        form.addRow("Sort Order", self.sort_order_spin)
        form.addRow("Instruction", self.instruction_edit)
        form.addRow("Expected Result", self.expected_result_edit)
        form.addRow("Hint Level", self.hint_level_combo)
        form.addRow("Hint Text", self.hint_text_edit)
        form.addRow("Measurement Unit", self.measurement_unit_edit)
        form.addRow("Notes", self.notes_edit)
        form.addRow("", self.requires_confirmation_check)
        form.addRow("", self.requires_measurement_check)
        form.addRow("", self.requires_photo_check)
        form.addRow("", self.is_active_check)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_step_template(self) -> None:
        row = self._step_template
        if row is None:
            self.step_number_spin.setValue(1)
            self.is_active_check.setChecked(True)
            return
        self.step_number_spin.setValue(row.step_number)
        self.sort_order_spin.setValue(row.sort_order or 0)
        self.instruction_edit.setPlainText(row.instruction)
        self.expected_result_edit.setPlainText(row.expected_result)
        self._set_combo_to_data(self.hint_level_combo, row.hint_level)
        self.hint_text_edit.setPlainText(row.hint_text)
        self.measurement_unit_edit.setText(row.measurement_unit)
        self.notes_edit.setPlainText(row.notes)
        self.requires_confirmation_check.setChecked(row.requires_confirmation)
        self.requires_measurement_check.setChecked(row.requires_measurement)
        self.requires_photo_check.setChecked(row.requires_photo)
        self.is_active_check.setChecked(row.is_active)

    def _validate_and_accept(self) -> None:
        if not self.instruction:
            QMessageBox.warning(self, "Step Template", "Instruction is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)
            return
        combo.setEditText(value)

    @property
    def step_number(self) -> int:
        return int(self.step_number_spin.value())

    @property
    def sort_order(self) -> int | None:
        value = int(self.sort_order_spin.value())
        return value or None

    @property
    def instruction(self) -> str:
        return self.instruction_edit.toPlainText().strip()

    @property
    def expected_result(self) -> str:
        return self.expected_result_edit.toPlainText().strip()

    @property
    def hint_level(self) -> str:
        value = self.hint_level_combo.currentData()
        if value is not None:
            return str(value).strip().upper()
        return self.hint_level_combo.currentText().strip().upper()

    @property
    def hint_text(self) -> str:
        return self.hint_text_edit.toPlainText().strip()

    @property
    def requires_confirmation(self) -> bool:
        return self.requires_confirmation_check.isChecked()

    @property
    def requires_measurement(self) -> bool:
        return self.requires_measurement_check.isChecked()

    @property
    def requires_photo(self) -> bool:
        return self.requires_photo_check.isChecked()

    @property
    def measurement_unit(self) -> str:
        return self.measurement_unit_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


__all__ = [
    "MaintenanceTaskStepTemplateEditDialog",
    "MaintenanceTaskTemplateEditDialog",
]
