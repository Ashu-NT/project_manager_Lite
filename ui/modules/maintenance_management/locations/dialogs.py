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
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenanceLocation,
)
from ui.modules.maintenance_management.shared import reset_combo_options
from src.ui.shared.widgets.code_generation import CodeFieldWidget


class MaintenanceLocationEditDialog(QDialog):
    def __init__(
        self,
        *,
        site_options: list[tuple[str, str]],
        locations: list[MaintenanceLocation],
        location: MaintenanceLocation | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._location = location
        self._site_options = list(site_options)
        self._locations = list(locations)
        self.setWindowTitle("Edit Location" if location is not None else "New Location")
        self.resize(560, 520)
        self._setup_ui()
        self._load_location()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Manage maintenance locations as owned operational hierarchy records for areas, buildings, units, and other maintainable places."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.location_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.location_code_field = CodeFieldWidget(
            prefix="LOC",
            line_edit=self.location_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.site_combo = QComboBox()
        for label, site_id in self._site_options:
            self.site_combo.addItem(label, site_id)
        self.parent_combo = QComboBox()
        self.location_type_edit = QLineEdit()
        self.criticality_combo = QComboBox()
        for value in MaintenanceCriticality:
            self.criticality_combo.addItem(value.value.title(), value.value)
        self.status_combo = QComboBox()
        for value in MaintenanceLifecycleStatus:
            self.status_combo.addItem(value.value.title(), value.value)
        self.description_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional location notes, routing guidance, or maintenance context.")
        self.is_active_check = QCheckBox("Active")

        form.addRow("Location Code", self.location_code_field)
        form.addRow("Name", self.name_edit)
        form.addRow("Site", self.site_combo)
        form.addRow("Parent Location", self.parent_combo)
        form.addRow("Location Type", self.location_type_edit)
        form.addRow("Criticality", self.criticality_combo)
        form.addRow("Status", self.status_combo)
        form.addRow("Description", self.description_edit)
        form.addRow("Notes", self.notes_edit)
        form.addRow("", self.is_active_check)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.site_combo.currentIndexChanged.connect(self._refresh_parent_options)

    def _load_location(self) -> None:
        location = self._location
        if location is None:
            self.criticality_combo.setCurrentText(MaintenanceCriticality.MEDIUM.value.title())
            self.status_combo.setCurrentText(MaintenanceLifecycleStatus.ACTIVE.value.title())
            self.is_active_check.setChecked(True)
            self._refresh_parent_options()
            return

        self.location_code_edit.setText(location.location_code)
        self.name_edit.setText(location.name)
        self._set_combo_to_data(self.site_combo, location.site_id)
        self.location_type_edit.setText(location.location_type)
        self._set_combo_to_data(self.criticality_combo, location.criticality.value)
        self._set_combo_to_data(self.status_combo, location.status.value)
        self.description_edit.setText(location.description)
        self.notes_edit.setPlainText(location.notes)
        self.is_active_check.setChecked(location.is_active)
        self._refresh_parent_options(selected_parent_id=location.parent_location_id)

    def _refresh_parent_options(self, _index: int | None = None, *, selected_parent_id: str | None = None) -> None:
        site_id = self.site_id
        options: list[tuple[str, str]] = []
        current_id = self._location.id if self._location is not None else None
        for row in self._locations:
            if row.site_id != site_id:
                continue
            if current_id is not None and row.id == current_id:
                continue
            options.append((f"{row.location_code} - {row.name}", row.id))
        reset_combo_options(
            self.parent_combo,
            placeholder="No parent location",
            options=options,
            selected_value=selected_parent_id,
        )

    def _validate_and_accept(self) -> None:
        if not self.location_code:
            QMessageBox.warning(self, "Location", "Location code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "Location", "Location name is required.")
            return
        if not self.site_id:
            QMessageBox.warning(self, "Location", "Site is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def location_code(self) -> str:
        return self.location_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def site_id(self) -> str:
        return str(self.site_combo.currentData() or "").strip()

    @property
    def parent_location_id(self) -> str | None:
        value = str(self.parent_combo.currentData() or "").strip()
        return value or None

    @property
    def location_type(self) -> str:
        return self.location_type_edit.text().strip()

    @property
    def criticality(self) -> str:
        return str(self.criticality_combo.currentData() or "").strip().upper()

    @property
    def status(self) -> str:
        return str(self.status_combo.currentData() or "").strip().upper()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


__all__ = ["MaintenanceLocationEditDialog"]
