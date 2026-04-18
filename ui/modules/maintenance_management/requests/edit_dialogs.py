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
    QVBoxLayout,
)

from core.modules.maintenance_management.domain import (
    MaintenancePriority,
    MaintenanceWorkOrderType,
    MaintenanceWorkRequest,
    MaintenanceWorkRequestSourceType,
)
from src.ui.shared.widgets.code_generation import CodeFieldWidget


class MaintenanceRequestEditDialog(QDialog):
    def __init__(
        self,
        *,
        site_options: list[tuple[str, str]],
        asset_options: list[tuple[str, str]],
        system_options: list[tuple[str, str]],
        location_options: list[tuple[str, str]],
        selected_site_id: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._selected_site_id = selected_site_id
        self.setWindowTitle("New Request")
        self.resize(620, 560)
        self._setup_ui(site_options, asset_options, system_options, location_options)

    def _setup_ui(
        self,
        site_options: list[tuple[str, str]],
        asset_options: list[tuple[str, str]],
        system_options: list[tuple[str, str]],
        location_options: list[tuple[str, str]],
    ) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Capture maintenance demand as a guided intake record, then convert it into a work order when planning is ready."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.request_code_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.request_code_field = CodeFieldWidget(
            prefix="WR",
            line_edit=self.request_code_edit,
            hint_getters=(lambda: self.title_edit.text(),),
        )
        self.site_combo = QComboBox()
        for label, site_id in site_options:
            self.site_combo.addItem(label, site_id)
        self.source_type_combo = QComboBox()
        for value in MaintenanceWorkRequestSourceType:
            self.source_type_combo.addItem(value.value.replace("_", " ").title(), value.value)
        self.request_type_edit = QLineEdit()
        self.asset_combo = QComboBox()
        self.asset_combo.addItem("No asset anchor", None)
        for label, asset_id in asset_options:
            self.asset_combo.addItem(label, asset_id)
        self.system_combo = QComboBox()
        self.system_combo.addItem("No system anchor", None)
        for label, system_id in system_options:
            self.system_combo.addItem(label, system_id)
        self.location_combo = QComboBox()
        self.location_combo.addItem("No location anchor", None)
        for label, location_id in location_options:
            self.location_combo.addItem(label, location_id)
        self.priority_combo = QComboBox()
        for value in MaintenancePriority:
            self.priority_combo.addItem(value.value.title(), value.value)
        self.description_edit = QLineEdit()
        self.failure_symptom_code_edit = QLineEdit()
        self.safety_risk_edit = QLineEdit()
        self.production_impact_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional intake notes, operator context, or triage guidance.")

        form.addRow("Request Code", self.request_code_field)
        form.addRow("Title", self.title_edit)
        form.addRow("Site", self.site_combo)
        form.addRow("Source Type", self.source_type_combo)
        form.addRow("Request Type", self.request_type_edit)
        form.addRow("Asset", self.asset_combo)
        form.addRow("System", self.system_combo)
        form.addRow("Location", self.location_combo)
        form.addRow("Priority", self.priority_combo)
        form.addRow("Description", self.description_edit)
        form.addRow("Failure Symptom", self.failure_symptom_code_edit)
        form.addRow("Safety Risk", self.safety_risk_edit)
        form.addRow("Production Impact", self.production_impact_edit)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        if self._selected_site_id:
            self._set_combo_to_data(self.site_combo, self._selected_site_id)
        self._set_combo_to_data(self.source_type_combo, MaintenanceWorkRequestSourceType.MANUAL.value)
        self._set_combo_to_data(self.priority_combo, MaintenancePriority.MEDIUM.value)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self.request_code:
            QMessageBox.warning(self, "Request", "Request code is required.")
            return
        if not self.site_id:
            QMessageBox.warning(self, "Request", "Site is required.")
            return
        if not self.request_type:
            QMessageBox.warning(self, "Request", "Request type is required.")
            return
        if not self.title:
            QMessageBox.warning(self, "Request", "Title is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def request_code(self) -> str:
        return self.request_code_edit.text().strip()

    @property
    def title(self) -> str:
        return self.title_edit.text().strip()

    @property
    def site_id(self) -> str:
        return str(self.site_combo.currentData() or "").strip()

    @property
    def source_type(self) -> str:
        return str(self.source_type_combo.currentData() or "").strip().upper()

    @property
    def request_type(self) -> str:
        return self.request_type_edit.text().strip()

    @property
    def asset_id(self) -> str | None:
        value = str(self.asset_combo.currentData() or "").strip()
        return value or None

    @property
    def system_id(self) -> str | None:
        value = str(self.system_combo.currentData() or "").strip()
        return value or None

    @property
    def location_id(self) -> str | None:
        value = str(self.location_combo.currentData() or "").strip()
        return value or None

    @property
    def priority(self) -> str:
        return str(self.priority_combo.currentData() or "").strip().upper()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def failure_symptom_code(self) -> str:
        return self.failure_symptom_code_edit.text().strip()

    @property
    def safety_risk_level(self) -> str:
        return self.safety_risk_edit.text().strip()

    @property
    def production_impact_level(self) -> str:
        return self.production_impact_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


class MaintenanceRequestConvertDialog(QDialog):
    def __init__(
        self,
        *,
        work_request: MaintenanceWorkRequest,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._work_request = work_request
        self.setWindowTitle("Convert Request to Work Order")
        self.resize(560, 440)
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Convert the selected maintenance request into a work order. Leave title or description blank to inherit them from the request."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.work_order_code_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.work_order_code_field = CodeFieldWidget(
            prefix="WO",
            line_edit=self.work_order_code_edit,
            hint_getters=(lambda: self.title_edit.text() or self._work_request.title,),
        )
        self.work_order_type_combo = QComboBox()
        for value in MaintenanceWorkOrderType:
            self.work_order_type_combo.addItem(value.value.replace("_", " ").title(), value.value)
        self.title_edit.setPlaceholderText(self._work_request.title or self._work_request.request_type.title())
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText(self._work_request.description or "Inherit request description")
        self.assigned_team_edit = QLineEdit()
        self.requires_shutdown_check = QCheckBox("Requires shutdown")
        self.permit_required_check = QCheckBox("Permit required")
        self.approval_required_check = QCheckBox("Approval required")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional planner note or conversion guidance.")

        form.addRow("Work Order Code", self.work_order_code_field)
        form.addRow("Work Order Type", self.work_order_type_combo)
        form.addRow("Title Override", self.title_edit)
        form.addRow("Description Override", self.description_edit)
        form.addRow("Assigned Team", self.assigned_team_edit)
        form.addRow("", self.requires_shutdown_check)
        form.addRow("", self.permit_required_check)
        form.addRow("", self.approval_required_check)
        form.addRow("Notes", self.notes_edit)
        root.addLayout(form)

        self._set_combo_to_data(self.work_order_type_combo, MaintenanceWorkOrderType.CORRECTIVE.value)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _validate_and_accept(self) -> None:
        if not self.work_order_code:
            QMessageBox.warning(self, "Convert Request", "Work order code is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def work_order_code(self) -> str:
        return self.work_order_code_edit.text().strip()

    @property
    def work_order_type(self) -> str:
        return str(self.work_order_type_combo.currentData() or "").strip().upper()

    @property
    def title(self) -> str:
        return self.title_edit.text().strip()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def assigned_team_id(self) -> str | None:
        value = self.assigned_team_edit.text().strip()
        return value or None

    @property
    def requires_shutdown(self) -> bool:
        return self.requires_shutdown_check.isChecked()

    @property
    def permit_required(self) -> bool:
        return self.permit_required_check.isChecked()

    @property
    def approval_required(self) -> bool:
        return self.approval_required_check.isChecked()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()


__all__ = ["MaintenanceRequestConvertDialog", "MaintenanceRequestEditDialog"]
