from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from core.modules.maintenance_management.domain import (
    MaintenanceAsset,
    MaintenanceAssetComponent,
    MaintenanceCriticality,
    MaintenanceLifecycleStatus,
    MaintenanceLocation,
    MaintenanceSystem,
)
from ui.modules.maintenance_management.shared import reset_combo_options
from ui.platform.shared.code_generation import CodeFieldWidget


class MaintenanceAssetEditDialog(QDialog):
    def __init__(
        self,
        *,
        site_options: list[tuple[str, str]],
        locations: list[MaintenanceLocation],
        systems: list[MaintenanceSystem],
        assets: list[MaintenanceAsset],
        asset: MaintenanceAsset | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._site_options = list(site_options)
        self._locations = list(locations)
        self._systems = list(systems)
        self._assets = list(assets)
        self._asset = asset
        self.setWindowTitle("Edit Asset" if asset is not None else "New Asset")
        self.resize(1000, 600)
        self._setup_ui()
        self._load_asset()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Author maintenance assets with their site, location, system, parent hierarchy, lifecycle, and execution strategy context."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        # Create two-column grid layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)

        # Left column fields
        self.asset_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.asset_code_field = CodeFieldWidget(
            prefix="AST",
            line_edit=self.asset_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.site_combo = QComboBox()
        for label, site_id in self._site_options:
            self.site_combo.addItem(label, site_id)
        self.location_combo = QComboBox()
        self.system_combo = QComboBox()
        self.parent_asset_combo = QComboBox()
        self.asset_type_edit = QLineEdit()
        self.asset_category_edit = QLineEdit()
        self.criticality_combo = QComboBox()
        for value in MaintenanceCriticality:
            self.criticality_combo.addItem(value.value.title(), value.value)
        self.status_combo = QComboBox()
        for value in MaintenanceLifecycleStatus:
            self.status_combo.addItem(value.value.title(), value.value)

        # Right column fields
        self.model_number_edit = QLineEdit()
        self.serial_number_edit = QLineEdit()
        self.barcode_edit = QLineEdit()
        self.maintenance_strategy_edit = QLineEdit()
        self.service_level_edit = QLineEdit()
        self.description_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional asset notes, planning context, or authoring guidance.")
        self.requires_shutdown_check = QCheckBox("Requires shutdown for major work")
        self.is_active_check = QCheckBox("Active")

        # Left column (rows 0-9)
        grid.addWidget(QLabel("Asset Code"), 0, 0)
        grid.addWidget(self.asset_code_field, 0, 1)
        grid.addWidget(QLabel("Name"), 1, 0)
        grid.addWidget(self.name_edit, 1, 1)
        grid.addWidget(QLabel("Site"), 2, 0)
        grid.addWidget(self.site_combo, 2, 1)
        grid.addWidget(QLabel("Location"), 3, 0)
        grid.addWidget(self.location_combo, 3, 1)
        grid.addWidget(QLabel("System"), 4, 0)
        grid.addWidget(self.system_combo, 4, 1)
        grid.addWidget(QLabel("Parent Asset"), 5, 0)
        grid.addWidget(self.parent_asset_combo, 5, 1)
        grid.addWidget(QLabel("Asset Type"), 6, 0)
        grid.addWidget(self.asset_type_edit, 6, 1)
        grid.addWidget(QLabel("Asset Category"), 7, 0)
        grid.addWidget(self.asset_category_edit, 7, 1)
        grid.addWidget(QLabel("Criticality"), 8, 0)
        grid.addWidget(self.criticality_combo, 8, 1)
        grid.addWidget(QLabel("Status"), 9, 0)
        grid.addWidget(self.status_combo, 9, 1)

        # Right column (rows 0-9)
        grid.addWidget(QLabel("Model Number"), 0, 2)
        grid.addWidget(self.model_number_edit, 0, 3)
        grid.addWidget(QLabel("Serial Number"), 1, 2)
        grid.addWidget(self.serial_number_edit, 1, 3)
        grid.addWidget(QLabel("Barcode"), 2, 2)
        grid.addWidget(self.barcode_edit, 2, 3)
        grid.addWidget(QLabel("Maintenance Strategy"), 3, 2)
        grid.addWidget(self.maintenance_strategy_edit, 3, 3)
        grid.addWidget(QLabel("Service Level"), 4, 2)
        grid.addWidget(self.service_level_edit, 4, 3)
        grid.addWidget(QLabel("Description"), 5, 2)
        grid.addWidget(self.description_edit, 5, 3)
        grid.addWidget(QLabel("Notes"), 6, 2)
        grid.addWidget(self.notes_edit, 6, 3, 2, 1)  # Span 2 rows
        grid.addWidget(self.requires_shutdown_check, 8, 2)
        grid.addWidget(self.is_active_check, 9, 2)

        root.addLayout(grid)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.site_combo.currentIndexChanged.connect(self._refresh_location_options)
        self.location_combo.currentIndexChanged.connect(self._refresh_system_options)
        self.system_combo.currentIndexChanged.connect(self._refresh_parent_options)

    def _load_asset(self) -> None:
        asset = self._asset
        if asset is None:
            self.criticality_combo.setCurrentText(MaintenanceCriticality.MEDIUM.value.title())
            self.status_combo.setCurrentText(MaintenanceLifecycleStatus.ACTIVE.value.title())
            self.is_active_check.setChecked(True)
            self._refresh_location_options()
            self._refresh_system_options()
            self._refresh_parent_options()
            return
        self.asset_code_edit.setText(asset.asset_code)
        self.name_edit.setText(asset.name)
        self._set_combo_to_data(self.site_combo, asset.site_id)
        self.asset_type_edit.setText(asset.asset_type)
        self.asset_category_edit.setText(asset.asset_category)
        self._set_combo_to_data(self.criticality_combo, asset.criticality.value)
        self._set_combo_to_data(self.status_combo, asset.status.value)
        self.model_number_edit.setText(asset.model_number)
        self.serial_number_edit.setText(asset.serial_number)
        self.barcode_edit.setText(asset.barcode)
        self.maintenance_strategy_edit.setText(asset.maintenance_strategy)
        self.service_level_edit.setText(asset.service_level)
        self.description_edit.setText(asset.description)
        self.notes_edit.setPlainText(asset.notes)
        self.requires_shutdown_check.setChecked(asset.requires_shutdown_for_major_work)
        self.is_active_check.setChecked(asset.is_active)
        self._refresh_location_options(selected_location_id=asset.location_id)
        self._refresh_system_options(selected_system_id=asset.system_id)
        self._refresh_parent_options(selected_parent_asset_id=asset.parent_asset_id)

    def _refresh_location_options(self, _index: int | None = None, *, selected_location_id: str | None = None) -> None:
        site_id = self.site_id
        options = [
            (f"{row.location_code} - {row.name}", row.id)
            for row in self._locations
            if row.site_id == site_id
        ]
        reset_combo_options(
            self.location_combo,
            placeholder="Select location",
            options=options,
            selected_value=selected_location_id,
        )
        self._refresh_system_options()

    def _refresh_system_options(self, _index: int | None = None, *, selected_system_id: str | None = None) -> None:
        site_id = self.site_id
        location_id = self.location_id
        options = [
            (f"{row.system_code} - {row.name}", row.id)
            for row in self._systems
            if row.site_id == site_id and (not location_id or row.location_id == location_id)
        ]
        reset_combo_options(
            self.system_combo,
            placeholder="No system",
            options=options,
            selected_value=selected_system_id,
        )
        self._refresh_parent_options()

    def _refresh_parent_options(
        self,
        _index: int | None = None,
        *,
        selected_parent_asset_id: str | None = None,
    ) -> None:
        site_id = self.site_id
        current_id = self._asset.id if self._asset is not None else None
        options = [
            (f"{row.asset_code} - {row.name}", row.id)
            for row in self._assets
            if row.site_id == site_id and row.id != current_id
        ]
        reset_combo_options(
            self.parent_asset_combo,
            placeholder="No parent asset",
            options=options,
            selected_value=selected_parent_asset_id,
        )

    def _validate_and_accept(self) -> None:
        if not self.asset_code:
            QMessageBox.warning(self, "Asset", "Asset code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "Asset", "Asset name is required.")
            return
        if not self.site_id:
            QMessageBox.warning(self, "Asset", "Site is required.")
            return
        if not self.location_id:
            QMessageBox.warning(self, "Asset", "Location is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str | None) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def asset_code(self) -> str:
        return self.asset_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def site_id(self) -> str:
        return str(self.site_combo.currentData() or "").strip()

    @property
    def location_id(self) -> str:
        return str(self.location_combo.currentData() or "").strip()

    @property
    def system_id(self) -> str | None:
        value = str(self.system_combo.currentData() or "").strip()
        return value or None

    @property
    def parent_asset_id(self) -> str | None:
        value = str(self.parent_asset_combo.currentData() or "").strip()
        return value or None

    @property
    def asset_type(self) -> str:
        return self.asset_type_edit.text().strip()

    @property
    def asset_category(self) -> str:
        return self.asset_category_edit.text().strip()

    @property
    def criticality(self) -> str:
        return str(self.criticality_combo.currentData() or "").strip().upper()

    @property
    def status(self) -> str:
        return str(self.status_combo.currentData() or "").strip().upper()

    @property
    def model_number(self) -> str:
        return self.model_number_edit.text().strip()

    @property
    def serial_number(self) -> str:
        return self.serial_number_edit.text().strip()

    @property
    def barcode(self) -> str:
        return self.barcode_edit.text().strip()

    @property
    def maintenance_strategy(self) -> str:
        return self.maintenance_strategy_edit.text().strip()

    @property
    def service_level(self) -> str:
        return self.service_level_edit.text().strip()

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def requires_shutdown_for_major_work(self) -> bool:
        return self.requires_shutdown_check.isChecked()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


class MaintenanceAssetComponentEditDialog(QDialog):
    def __init__(
        self,
        *,
        components: list[MaintenanceAssetComponent],
        component: MaintenanceAssetComponent | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._components = list(components)
        self._component = component
        self.setWindowTitle("Edit Component" if component is not None else "New Component")
        self.resize(660, 660)
        self._setup_ui()
        self._load_component()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Author maintainable components that sit under the selected asset and support detailed work-order execution."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.component_code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.component_code_field = CodeFieldWidget(
            prefix="CMP",
            line_edit=self.component_code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.parent_component_combo = QComboBox()
        self.component_type_edit = QLineEdit()
        self.status_combo = QComboBox()
        for value in MaintenanceLifecycleStatus:
            self.status_combo.addItem(value.value.title(), value.value)
        self.manufacturer_part_number_edit = QLineEdit()
        self.supplier_part_number_edit = QLineEdit()
        self.model_number_edit = QLineEdit()
        self.serial_number_edit = QLineEdit()
        self.expected_life_hours_spin = QSpinBox()
        self.expected_life_hours_spin.setRange(0, 1000000)
        self.expected_life_hours_spin.setSpecialValueText("Not set")
        self.expected_life_cycles_spin = QSpinBox()
        self.expected_life_cycles_spin.setRange(0, 1000000)
        self.expected_life_cycles_spin.setSpecialValueText("Not set")
        self.description_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional component notes and service guidance.")
        self.is_critical_component_check = QCheckBox("Critical component")
        self.is_active_check = QCheckBox("Active")

        form.addRow("Component Code", self.component_code_field)
        form.addRow("Name", self.name_edit)
        form.addRow("Parent Component", self.parent_component_combo)
        form.addRow("Component Type", self.component_type_edit)
        form.addRow("Status", self.status_combo)
        form.addRow("Manufacturer Part No.", self.manufacturer_part_number_edit)
        form.addRow("Supplier Part No.", self.supplier_part_number_edit)
        form.addRow("Model Number", self.model_number_edit)
        form.addRow("Serial Number", self.serial_number_edit)
        form.addRow("Expected Life Hours", self.expected_life_hours_spin)
        form.addRow("Expected Life Cycles", self.expected_life_cycles_spin)
        form.addRow("Description", self.description_edit)
        form.addRow("Notes", self.notes_edit)
        form.addRow("", self.is_critical_component_check)
        form.addRow("", self.is_active_check)
        root.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_component(self) -> None:
        current_id = self._component.id if self._component is not None else None
        options = [
            (f"{row.component_code} - {row.name}", row.id)
            for row in self._components
            if row.id != current_id
        ]
        reset_combo_options(
            self.parent_component_combo,
            placeholder="No parent component",
            options=options,
            selected_value=self._component.parent_component_id if self._component is not None else None,
        )
        component = self._component
        if component is None:
            self.status_combo.setCurrentText(MaintenanceLifecycleStatus.ACTIVE.value.title())
            self.is_active_check.setChecked(True)
            return
        self.component_code_edit.setText(component.component_code)
        self.name_edit.setText(component.name)
        self.component_type_edit.setText(component.component_type)
        self._set_combo_to_data(self.status_combo, component.status.value)
        self.manufacturer_part_number_edit.setText(component.manufacturer_part_number)
        self.supplier_part_number_edit.setText(component.supplier_part_number)
        self.model_number_edit.setText(component.model_number)
        self.serial_number_edit.setText(component.serial_number)
        self.expected_life_hours_spin.setValue(component.expected_life_hours or 0)
        self.expected_life_cycles_spin.setValue(component.expected_life_cycles or 0)
        self.description_edit.setText(component.description)
        self.notes_edit.setPlainText(component.notes)
        self.is_critical_component_check.setChecked(component.is_critical_component)
        self.is_active_check.setChecked(component.is_active)

    def _validate_and_accept(self) -> None:
        if not self.component_code:
            QMessageBox.warning(self, "Component", "Component code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "Component", "Component name is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value: str | None) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def component_code(self) -> str:
        return self.component_code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def parent_component_id(self) -> str | None:
        value = str(self.parent_component_combo.currentData() or "").strip()
        return value or None

    @property
    def component_type(self) -> str:
        return self.component_type_edit.text().strip()

    @property
    def status(self) -> str:
        return str(self.status_combo.currentData() or "").strip().upper()

    @property
    def manufacturer_part_number(self) -> str:
        return self.manufacturer_part_number_edit.text().strip()

    @property
    def supplier_part_number(self) -> str:
        return self.supplier_part_number_edit.text().strip()

    @property
    def model_number(self) -> str:
        return self.model_number_edit.text().strip()

    @property
    def serial_number(self) -> str:
        return self.serial_number_edit.text().strip()

    @property
    def expected_life_hours(self) -> int | None:
        value = int(self.expected_life_hours_spin.value())
        return value or None

    @property
    def expected_life_cycles(self) -> int | None:
        value = int(self.expected_life_cycles_spin.value())
        return value or None

    @property
    def description(self) -> str:
        return self.description_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_critical_component(self) -> bool:
        return self.is_critical_component_check.isChecked()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


__all__ = [
    "MaintenanceAssetComponentEditDialog",
    "MaintenanceAssetEditDialog",
]
