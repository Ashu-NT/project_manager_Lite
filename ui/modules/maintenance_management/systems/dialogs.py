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
    MaintenanceSystem,
)
from ui.modules.maintenance_management.shared import reset_combo_options
from src.ui.shared.widgets.code_generation import CodeFieldWidget


class MaintenanceSystemEditDialog(QDialog):
    def __init__(
        self,
        *,
        site_options: list[tuple[str, str]],
        locations: list[MaintenanceLocation],
        systems: list[MaintenanceSystem],
        system: MaintenanceSystem | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._system = system
        self._site_options = list(site_options)
        self._locations = list(locations)
        self._systems = list(systems)
        self.setWindowTitle("Edit System" if system is not None else "New System")
        self.resize(580, 540)
        self._setup_ui()
        self._load_system()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Manage functional maintenance systems that group process, utility, and equipment structure beneath site and location context."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.system_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.system_code_field = CodeFieldWidget(
            prefix="SYS",
            line_edit=self.system_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.site_combo = QComboBox()
        for label, site_id in self._site_options:
            self.site_combo.addItem(label, site_id)
        self.location_combo = QComboBox()
        self.parent_combo = QComboBox()
        self.system_type_edit = QLineEdit()
        self.criticality_combo = QComboBox()
        for value in MaintenanceCriticality:
            self.criticality_combo.addItem(value.value.title(), value.value)
        self.status_combo = QComboBox()
        for value in MaintenanceLifecycleStatus:
            self.status_combo.addItem(value.value.title(), value.value)
        self.description_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional system notes, process coverage, or planning hints.")
        self.is_active_check = QCheckBox("Active")

        form.addRow("System Code", self.system_code_field)
        form.addRow("Name", self.name_edit)
        form.addRow("Site", self.site_combo)
        form.addRow("Location", self.location_combo)
        form.addRow("Parent System", self.parent_combo)
        form.addRow("System Type", self.system_type_edit)
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

        self.site_combo.currentIndexChanged.connect(self._refresh_location_and_parent_options)
        self.location_combo.currentIndexChanged.connect(self._refresh_parent_options)

    def _load_system(self) -> None:
        system = self._system
        if system is None:
            self.criticality_combo.setCurrentText(MaintenanceCriticality.MEDIUM.value.title())
            self.status_combo.setCurrentText(MaintenanceLifecycleStatus.ACTIVE.value.title())
            self.is_active_check.setChecked(True)
            self._refresh_location_and_parent_options()
            return

        self.system_code_edit.setText(system.system_code)
        self.name_edit.setText(system.name)
        self._set_combo_to_data(self.site_combo, system.site_id)
        self.system_type_edit.setText(system.system_type)
        self._set_combo_to_data(self.criticality_combo, system.criticality.value)
        self._set_combo_to_data(self.status_combo, system.status.value)
        self.description_edit.setText(system.description)
        self.notes_edit.setPlainText(system.notes)
        self.is_active_check.setChecked(system.is_active)
        self._refresh_location_and_parent_options(selected_location_id=system.location_id, selected_parent_id=system.parent_system_id)

    def _refresh_location_and_parent_options(
        self,
        _index: int | None = None,
        *,
        selected_location_id: str | None = None,
        selected_parent_id: str | None = None,
    ) -> None:
        site_id = self.site_id
        location_options = [
            (f"{row.location_code} - {row.name}", row.id)
            for row in self._locations
            if row.site_id == site_id
        ]
        reset_combo_options(
            self.location_combo,
            placeholder="No linked location",
            options=location_options,
            selected_value=selected_location_id,
        )
        self._refresh_parent_options(selected_parent_id=selected_parent_id)

    def _refresh_parent_options(self, _index: int | None = None, *, selected_parent_id: str | None = None) -> None:
        site_id = self.site_id
        location_id = self.location_id
        current_id = self._system.id if self._system is not None else None
        options: list[tuple[str, str]] = []
        for row in self._systems:
            if row.site_id != site_id:
                continue
            if current_id is not None and row.id == current_id:
                continue
            if location_id and row.location_id not in (None, location_id):
                continue
            options.append((f"{row.system_code} - {row.name}", row.id))
        reset_combo_options(
            self.parent_combo,
            placeholder="No parent system",
            options=options,
            selected_value=selected_parent_id,
        )

    def _validate_and_accept(self) -> None:
        if not self.system_code:
            QMessageBox.warning(self, "System", "System code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "System", "System name is required.")
            return
        if not self.site_id:
            QMessageBox.warning(self, "System", "Site is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str | None) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def system_code(self) -> str:
        return self.system_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def site_id(self) -> str:
        return str(self.site_combo.currentData() or "").strip()

    @property
    def location_id(self) -> str | None:
        value = str(self.location_combo.currentData() or "").strip()
        return value or None

    @property
    def parent_system_id(self) -> str | None:
        value = str(self.parent_combo.currentData() or "").strip()
        return value or None

    @property
    def system_type(self) -> str:
        return self.system_type_edit.text().strip()

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


__all__ = ["MaintenanceSystemEditDialog"]
