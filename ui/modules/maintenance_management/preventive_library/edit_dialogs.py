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
    MaintenanceCalendarFrequencyUnit,
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePlanType,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenancePriority,
    MaintenanceSchedulePolicy,
    MaintenanceSensorDirection,
    MaintenanceTriggerMode,
)
from ui.platform.shared.code_generation import CodeFieldWidget


class MaintenancePreventivePlanEditDialog(QDialog):
    def __init__(
        self,
        *,
        sites,
        assets,
        components,
        systems,
        sensors,
        preventive_plan: MaintenancePreventivePlan | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._sites = list(sites)
        self._assets = list(assets)
        self._components = list(components)
        self._systems = list(systems)
        self._sensors = list(sensors)
        self._preventive_plan = preventive_plan
        self.setWindowTitle("Edit Preventive Plan" if preventive_plan is not None else "New Preventive Plan")
        self.resize(1200, 700)
        self._setup_ui()
        self._load_preventive_plan()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
    
        intro = QLabel(
            "Author preventive-plan libraries for calendar, sensor, and hybrid generation. "
            "Use the detail popup later to manage the selected plan's task library."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        # Create two-column grid layout
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)

        # Initialize all form fields
        self.code_edit = QLineEdit()
        self.name_edit = QLineEdit()
        self.code_field = CodeFieldWidget(
            prefix="PP",
            line_edit=self.code_edit,
            hint_getters=(lambda: self.name_edit.text(),),
        )
        self.site_combo = QComboBox()
        self.asset_combo = QComboBox()
        self.component_combo = QComboBox()
        self.system_combo = QComboBox()
        self.status_combo = QComboBox()
        self.plan_type_combo = QComboBox()
        self.priority_combo = QComboBox()
        self.trigger_mode_combo = QComboBox()
        self.schedule_policy_combo = QComboBox()
        self.calendar_unit_combo = QComboBox()
        self.calendar_value_spin = QSpinBox()
        self.generation_horizon_spin = QSpinBox()
        self.sensor_combo = QComboBox()
        self.sensor_threshold_edit = QLineEdit()
        self.sensor_direction_combo = QComboBox()
        self.sensor_reset_rule_edit = QLineEdit()
        self.description_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional planner notes, shutdown guidance, or trigger commentary.")
        self.requires_shutdown_check = QCheckBox("Requires shutdown")
        self.approval_required_check = QCheckBox("Approval required")
        self.auto_generate_work_order_check = QCheckBox("Auto-generate work order")
        self.is_active_check = QCheckBox("Active")

        self.calendar_value_spin.setRange(0, 100000)
        self.calendar_value_spin.setSpecialValueText("Not set")
        self.generation_horizon_spin.setRange(1, 52)
        self.generation_horizon_spin.setValue(13)
        self.sensor_threshold_edit.setPlaceholderText("Example: 1000 or 75.5")

        # Populate combo boxes
        for label, value in ((f"{site.site_code} - {site.name}", site.id) for site in self._sites):
            self.site_combo.addItem(label, value)
        self.asset_combo.addItem("No asset anchor", None)
        self.component_combo.addItem("No component anchor", None)
        self.system_combo.addItem("No system anchor", None)
        for value in MaintenancePlanStatus:
            self.status_combo.addItem(value.value.title(), value.value)
        for value in MaintenancePlanType:
            self.plan_type_combo.addItem(value.value.replace("_", " ").title(), value.value)
        for value in MaintenancePriority:
            self.priority_combo.addItem(value.value.title(), value.value)
        for value in MaintenanceTriggerMode:
            self.trigger_mode_combo.addItem(value.value.title(), value.value)
        for value in MaintenanceSchedulePolicy:
            self.schedule_policy_combo.addItem(value.value.title(), value.value)
        self.calendar_unit_combo.addItem("No calendar rule", None)
        for value in MaintenanceCalendarFrequencyUnit:
            self.calendar_unit_combo.addItem(value.value.replace("_", " ").title(), value.value)
        self.sensor_combo.addItem("No sensor rule", None)
        self.sensor_direction_combo.addItem("No direction", None)
        for value in MaintenanceSensorDirection:
            self.sensor_direction_combo.addItem(value.value.replace("_", " ").title(), value.value)

        # Left column - Basic Info and Settings
        grid.addWidget(QLabel("Plan Code"), 0, 0)
        grid.addWidget(self.code_field, 0, 1)
        grid.addWidget(QLabel("Name"), 1, 0)
        grid.addWidget(self.name_edit, 1, 1)
        grid.addWidget(QLabel("Site"), 2, 0)
        grid.addWidget(self.site_combo, 2, 1)
        grid.addWidget(QLabel("Asset"), 3, 0)
        grid.addWidget(self.asset_combo, 3, 1)
        grid.addWidget(QLabel("Component"), 4, 0)
        grid.addWidget(self.component_combo, 4, 1)
        grid.addWidget(QLabel("System"), 5, 0)
        grid.addWidget(self.system_combo, 5, 1)
        grid.addWidget(QLabel("Status"), 6, 0)
        grid.addWidget(self.status_combo, 6, 1)
        grid.addWidget(QLabel("Plan Type"), 7, 0)
        grid.addWidget(self.plan_type_combo, 7, 1)
        grid.addWidget(QLabel("Priority"), 8, 0)
        grid.addWidget(self.priority_combo, 8, 1)
        grid.addWidget(QLabel("Trigger Mode"), 9, 0)
        grid.addWidget(self.trigger_mode_combo, 9, 1)
        grid.addWidget(QLabel("Schedule Policy"), 10, 0)
        grid.addWidget(self.schedule_policy_combo, 10, 1)

        # Right column - Triggers and Options
        grid.addWidget(QLabel("Calendar Unit"), 0, 2)
        grid.addWidget(self.calendar_unit_combo, 0, 3)
        grid.addWidget(QLabel("Calendar Value"), 1, 2)
        grid.addWidget(self.calendar_value_spin, 1, 3)
        grid.addWidget(QLabel("Generation Horizon"), 2, 2)
        grid.addWidget(self.generation_horizon_spin, 2, 3)
        grid.addWidget(QLabel("Sensor"), 3, 2)
        grid.addWidget(self.sensor_combo, 3, 3)
        grid.addWidget(QLabel("Sensor Threshold"), 4, 2)
        grid.addWidget(self.sensor_threshold_edit, 4, 3)
        grid.addWidget(QLabel("Sensor Direction"), 5, 2)
        grid.addWidget(self.sensor_direction_combo, 5, 3)
        grid.addWidget(QLabel("Sensor Reset Rule"), 6, 2)
        grid.addWidget(self.sensor_reset_rule_edit, 6, 3)
        grid.addWidget(QLabel("Description"), 7, 2)
        grid.addWidget(self.description_edit, 7, 3)
        grid.addWidget(QLabel("Notes"), 8, 2)
        grid.addWidget(self.notes_edit, 8, 3, 2, 1)  # Span 2 rows

        # Checkboxes at bottom
        grid.addWidget(self.requires_shutdown_check, 10, 2)
        grid.addWidget(self.approval_required_check, 10, 3)
        grid.addWidget(self.auto_generate_work_order_check, 11, 2)
        grid.addWidget(self.is_active_check, 11, 3)

        root.addLayout(grid)

        self.site_combo.currentIndexChanged.connect(self._refresh_context_options)
        self.asset_combo.currentIndexChanged.connect(self._refresh_component_options)
        self.trigger_mode_combo.currentIndexChanged.connect(self._sync_trigger_mode_state)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_preventive_plan(self) -> None:
        row = self._preventive_plan
        if row is None:
            self._refresh_context_options()
            self._set_combo_to_data(self.status_combo, MaintenancePlanStatus.DRAFT.value)
            self._set_combo_to_data(self.plan_type_combo, MaintenancePlanType.PREVENTIVE.value)
            self._set_combo_to_data(self.priority_combo, MaintenancePriority.MEDIUM.value)
            self._set_combo_to_data(self.trigger_mode_combo, MaintenanceTriggerMode.CALENDAR.value)
            self._set_combo_to_data(self.schedule_policy_combo, MaintenanceSchedulePolicy.FIXED.value)
            self.is_active_check.setChecked(True)
            self._sync_trigger_mode_state()
            return
        self.code_edit.setText(row.plan_code)
        self.name_edit.setText(row.name)
        self._set_combo_to_data(self.site_combo, row.site_id)
        self._refresh_context_options()
        self._set_combo_to_data(self.asset_combo, row.asset_id)
        self._refresh_component_options()
        self._set_combo_to_data(self.component_combo, row.component_id)
        self._set_combo_to_data(self.system_combo, row.system_id)
        self._set_combo_to_data(self.status_combo, row.status.value)
        self._set_combo_to_data(self.plan_type_combo, row.plan_type.value)
        self._set_combo_to_data(self.priority_combo, row.priority.value)
        self._set_combo_to_data(self.trigger_mode_combo, row.trigger_mode.value)
        self._set_combo_to_data(self.schedule_policy_combo, row.schedule_policy.value)
        self._set_combo_to_data(
            self.calendar_unit_combo,
            row.calendar_frequency_unit.value if row.calendar_frequency_unit is not None else None,
        )
        self.calendar_value_spin.setValue(row.calendar_frequency_value or 0)
        self.generation_horizon_spin.setValue(max(row.generation_horizon_count, 1))
        self._set_combo_to_data(self.sensor_combo, row.sensor_id)
        self.sensor_threshold_edit.setText("" if row.sensor_threshold is None else str(row.sensor_threshold))
        self._set_combo_to_data(
            self.sensor_direction_combo,
            row.sensor_direction.value if row.sensor_direction is not None else None,
        )
        self.sensor_reset_rule_edit.setText(row.sensor_reset_rule)
        self.description_edit.setText(row.description)
        self.notes_edit.setPlainText(row.notes)
        self.requires_shutdown_check.setChecked(row.requires_shutdown)
        self.approval_required_check.setChecked(row.approval_required)
        self.auto_generate_work_order_check.setChecked(row.auto_generate_work_order)
        self.is_active_check.setChecked(row.is_active)
        self._sync_trigger_mode_state()

    def _refresh_context_options(self) -> None:
        selected_site_id = self.site_id
        selected_asset_id = self.asset_id
        assets = [row for row in self._assets if selected_site_id in (None, row.site_id)]
        systems = [row for row in self._systems if selected_site_id in (None, row.site_id)]
        sensors = [row for row in self._sensors if selected_site_id in (None, row.site_id)]

        self.asset_combo.blockSignals(True)
        self.asset_combo.clear()
        self.asset_combo.addItem("No asset anchor", None)
        for row in assets:
            self.asset_combo.addItem(f"{row.asset_code} - {row.name}", row.id)
        self._set_combo_to_data(self.asset_combo, selected_asset_id)
        self.asset_combo.blockSignals(False)

        self.system_combo.blockSignals(True)
        self.system_combo.clear()
        self.system_combo.addItem("No system anchor", None)
        for row in systems:
            self.system_combo.addItem(f"{row.system_code} - {row.name}", row.id)
        self._set_combo_to_data(self.system_combo, self.system_id)
        self.system_combo.blockSignals(False)

        self.sensor_combo.blockSignals(True)
        self.sensor_combo.clear()
        self.sensor_combo.addItem("No sensor rule", None)
        for row in sensors:
            self.sensor_combo.addItem(f"{row.sensor_code} - {row.sensor_name}", row.id)
        self._set_combo_to_data(self.sensor_combo, self.sensor_id)
        self.sensor_combo.blockSignals(False)

        self._refresh_component_options()

    def _refresh_component_options(self) -> None:
        selected_site_id = self.site_id
        selected_asset_id = self.asset_id
        selected_component_id = self.component_id
        asset_site_map = {row.id: row.site_id for row in self._assets}
        components = []
        for row in self._components:
            if selected_asset_id is not None and row.asset_id != selected_asset_id:
                continue
            if selected_asset_id is None and selected_site_id is not None and asset_site_map.get(row.asset_id) != selected_site_id:
                continue
            components.append(row)
        self.component_combo.blockSignals(True)
        self.component_combo.clear()
        self.component_combo.addItem("No component anchor", None)
        for row in components:
            self.component_combo.addItem(f"{row.component_code} - {row.name}", row.id)
        self._set_combo_to_data(self.component_combo, selected_component_id)
        self.component_combo.blockSignals(False)

    def _sync_trigger_mode_state(self) -> None:
        trigger_mode = self.trigger_mode
        calendar_enabled = trigger_mode in {"CALENDAR", "HYBRID"}
        sensor_enabled = trigger_mode in {"SENSOR", "HYBRID"}
        self.calendar_unit_combo.setEnabled(calendar_enabled)
        self.calendar_value_spin.setEnabled(calendar_enabled)
        self.sensor_combo.setEnabled(sensor_enabled)
        self.sensor_threshold_edit.setEnabled(sensor_enabled)
        self.sensor_direction_combo.setEnabled(sensor_enabled)
        self.sensor_reset_rule_edit.setEnabled(sensor_enabled)

    def _validate_and_accept(self) -> None:
        if not self.site_id:
            QMessageBox.warning(self, "Preventive Plan", "Site is required.")
            return
        if not self.plan_code:
            QMessageBox.warning(self, "Preventive Plan", "Preventive plan code is required.")
            return
        if not self.name:
            QMessageBox.warning(self, "Preventive Plan", "Preventive plan name is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def plan_code(self) -> str:
        return self.code_edit.text().strip()

    @property
    def name(self) -> str:
        return self.name_edit.text().strip()

    @property
    def site_id(self) -> str | None:
        value = self.site_combo.currentData()
        return str(value).strip() if value else None

    @property
    def asset_id(self) -> str | None:
        value = self.asset_combo.currentData()
        return str(value).strip() if value else None

    @property
    def component_id(self) -> str | None:
        value = self.component_combo.currentData()
        return str(value).strip() if value else None

    @property
    def system_id(self) -> str | None:
        value = self.system_combo.currentData()
        return str(value).strip() if value else None

    @property
    def status(self) -> str:
        return str(self.status_combo.currentData() or "").strip().upper()

    @property
    def plan_type(self) -> str:
        return str(self.plan_type_combo.currentData() or "").strip().upper()

    @property
    def priority(self) -> str:
        return str(self.priority_combo.currentData() or "").strip().upper()

    @property
    def trigger_mode(self) -> str:
        return str(self.trigger_mode_combo.currentData() or "").strip().upper()

    @property
    def schedule_policy(self) -> str:
        return str(self.schedule_policy_combo.currentData() or "").strip().upper()

    @property
    def calendar_frequency_unit(self) -> str | None:
        if self.trigger_mode not in {"CALENDAR", "HYBRID"}:
            return None
        value = self.calendar_unit_combo.currentData()
        return str(value).strip().upper() if value else None

    @property
    def calendar_frequency_value(self) -> int | None:
        if self.trigger_mode not in {"CALENDAR", "HYBRID"}:
            return None
        value = int(self.calendar_value_spin.value())
        return value or None

    @property
    def generation_horizon_count(self) -> int:
        return max(1, int(self.generation_horizon_spin.value()))

    @property
    def sensor_id(self) -> str | None:
        if self.trigger_mode not in {"SENSOR", "HYBRID"}:
            return None
        value = self.sensor_combo.currentData()
        return str(value).strip() if value else None

    @property
    def sensor_threshold(self) -> str | None:
        if self.trigger_mode not in {"SENSOR", "HYBRID"}:
            return None
        value = self.sensor_threshold_edit.text().strip()
        return value or None

    @property
    def sensor_direction(self) -> str | None:
        if self.trigger_mode not in {"SENSOR", "HYBRID"}:
            return None
        value = self.sensor_direction_combo.currentData()
        return str(value).strip().upper() if value else None

    @property
    def sensor_reset_rule(self) -> str:
        return self.sensor_reset_rule_edit.text().strip()

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
    def approval_required(self) -> bool:
        return self.approval_required_check.isChecked()

    @property
    def auto_generate_work_order(self) -> bool:
        return self.auto_generate_work_order_check.isChecked()

    @property
    def is_active(self) -> bool:
        return self.is_active_check.isChecked()


class MaintenancePreventivePlanTaskEditDialog(QDialog):
    def __init__(
        self,
        *,
        task_template_options: list[tuple[str, str]],
        sensor_options: list[tuple[str, str]],
        plan_task: MaintenancePreventivePlanTask | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._task_template_options = list(task_template_options)
        self._sensor_options = list(sensor_options)
        self._plan_task = plan_task
        self.setWindowTitle("Edit Plan Task" if plan_task is not None else "New Plan Task")
        self.resize(680, 700)
        self._setup_ui()
        self._load_plan_task()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        intro = QLabel(
            "Attach reusable task templates to the selected preventive plan and define task-level trigger overrides only when they differ from the parent plan."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        form = QFormLayout()
        self.task_template_combo = QComboBox()
        self.sequence_spin = QSpinBox()
        self.sequence_spin.setRange(1, 999)
        self.trigger_scope_combo = QComboBox()
        self.trigger_mode_combo = QComboBox()
        self.calendar_unit_combo = QComboBox()
        self.calendar_value_spin = QSpinBox()
        self.sensor_combo = QComboBox()
        self.sensor_threshold_edit = QLineEdit()
        self.sensor_direction_combo = QComboBox()
        self.estimated_minutes_spin = QSpinBox()
        self.estimated_minutes_spin.setRange(0, 100000)
        self.estimated_minutes_spin.setSpecialValueText("Use template estimate")
        self.default_assigned_team_edit = QLineEdit()
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Optional override notes, planner intent, or shutdown context.")
        self.is_mandatory_check = QCheckBox("Mandatory")

        for label, value in self._task_template_options:
            self.task_template_combo.addItem(label, value)
        for value in MaintenancePlanTaskTriggerScope:
            self.trigger_scope_combo.addItem(value.value.replace("_", " ").title(), value.value)
        self.trigger_mode_combo.addItem("Use plan trigger", None)
        for value in MaintenanceTriggerMode:
            self.trigger_mode_combo.addItem(value.value.title(), value.value)
        self.calendar_unit_combo.addItem("No calendar override", None)
        for value in MaintenanceCalendarFrequencyUnit:
            self.calendar_unit_combo.addItem(value.value.replace("_", " ").title(), value.value)
        self.calendar_value_spin.setRange(0, 100000)
        self.calendar_value_spin.setSpecialValueText("Not set")
        self.sensor_combo.addItem("No sensor override", None)
        for label, value in self._sensor_options:
            self.sensor_combo.addItem(label, value)
        self.sensor_direction_combo.addItem("No direction", None)
        for value in MaintenanceSensorDirection:
            self.sensor_direction_combo.addItem(value.value.replace("_", " ").title(), value.value)

        form.addRow("Task Template", self.task_template_combo)
        form.addRow("Sequence", self.sequence_spin)
        form.addRow("Trigger Scope", self.trigger_scope_combo)
        form.addRow("Trigger Mode Override", self.trigger_mode_combo)
        form.addRow("Calendar Unit Override", self.calendar_unit_combo)
        form.addRow("Calendar Value Override", self.calendar_value_spin)
        form.addRow("Sensor Override", self.sensor_combo)
        form.addRow("Sensor Threshold Override", self.sensor_threshold_edit)
        form.addRow("Sensor Direction Override", self.sensor_direction_combo)
        form.addRow("Estimated Minutes Override", self.estimated_minutes_spin)
        form.addRow("Default Team", self.default_assigned_team_edit)
        form.addRow("Notes", self.notes_edit)
        form.addRow("", self.is_mandatory_check)
        root.addLayout(form)

        self.trigger_scope_combo.currentIndexChanged.connect(self._sync_override_state)
        self.trigger_mode_combo.currentIndexChanged.connect(self._sync_override_state)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _load_plan_task(self) -> None:
        row = self._plan_task
        if row is None:
            self.sequence_spin.setValue(1)
            self._set_combo_to_data(self.trigger_scope_combo, MaintenancePlanTaskTriggerScope.INHERIT_PLAN.value)
            self.is_mandatory_check.setChecked(True)
            self._sync_override_state()
            return
        self._set_combo_to_data(self.task_template_combo, row.task_template_id)
        self.sequence_spin.setValue(row.sequence_no)
        self._set_combo_to_data(self.trigger_scope_combo, row.trigger_scope.value)
        self._set_combo_to_data(
            self.trigger_mode_combo,
            row.trigger_mode_override.value if row.trigger_mode_override is not None else None,
        )
        self._set_combo_to_data(
            self.calendar_unit_combo,
            row.calendar_frequency_unit_override.value if row.calendar_frequency_unit_override is not None else None,
        )
        self.calendar_value_spin.setValue(row.calendar_frequency_value_override or 0)
        self._set_combo_to_data(self.sensor_combo, row.sensor_id_override)
        self.sensor_threshold_edit.setText("" if row.sensor_threshold_override is None else str(row.sensor_threshold_override))
        self._set_combo_to_data(
            self.sensor_direction_combo,
            row.sensor_direction_override.value if row.sensor_direction_override is not None else None,
        )
        self.estimated_minutes_spin.setValue(row.estimated_minutes_override or 0)
        self.default_assigned_team_edit.setText(row.default_assigned_team_id or "")
        self.notes_edit.setPlainText(row.notes)
        self.is_mandatory_check.setChecked(row.is_mandatory)
        self._sync_override_state()

    def _sync_override_state(self) -> None:
        is_override = self.trigger_scope == "TASK_OVERRIDE"
        trigger_mode = self.trigger_mode_override
        self.trigger_mode_combo.setEnabled(is_override)
        calendar_enabled = is_override and trigger_mode in {"CALENDAR", "HYBRID"}
        sensor_enabled = is_override and trigger_mode in {"SENSOR", "HYBRID"}
        self.calendar_unit_combo.setEnabled(calendar_enabled)
        self.calendar_value_spin.setEnabled(calendar_enabled)
        self.sensor_combo.setEnabled(sensor_enabled)
        self.sensor_threshold_edit.setEnabled(sensor_enabled)
        self.sensor_direction_combo.setEnabled(sensor_enabled)

    def _validate_and_accept(self) -> None:
        if not self.task_template_id:
            QMessageBox.warning(self, "Plan Task", "Task template is required.")
            return
        self.accept()

    @staticmethod
    def _set_combo_to_data(combo: QComboBox, value) -> None:
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @property
    def task_template_id(self) -> str | None:
        value = self.task_template_combo.currentData()
        return str(value).strip() if value else None

    @property
    def sequence_no(self) -> int:
        return int(self.sequence_spin.value())

    @property
    def trigger_scope(self) -> str:
        return str(self.trigger_scope_combo.currentData() or "").strip().upper()

    @property
    def trigger_mode_override(self) -> str | None:
        if self.trigger_scope != "TASK_OVERRIDE":
            return None
        value = self.trigger_mode_combo.currentData()
        return str(value).strip().upper() if value else None

    @property
    def calendar_frequency_unit_override(self) -> str | None:
        if self.trigger_scope != "TASK_OVERRIDE" or self.trigger_mode_override not in {"CALENDAR", "HYBRID"}:
            return None
        value = self.calendar_unit_combo.currentData()
        return str(value).strip().upper() if value else None

    @property
    def calendar_frequency_value_override(self) -> int | None:
        if self.trigger_scope != "TASK_OVERRIDE" or self.trigger_mode_override not in {"CALENDAR", "HYBRID"}:
            return None
        value = int(self.calendar_value_spin.value())
        return value or None

    @property
    def sensor_id_override(self) -> str | None:
        if self.trigger_scope != "TASK_OVERRIDE" or self.trigger_mode_override not in {"SENSOR", "HYBRID"}:
            return None
        value = self.sensor_combo.currentData()
        return str(value).strip() if value else None

    @property
    def sensor_threshold_override(self) -> str | None:
        if self.trigger_scope != "TASK_OVERRIDE" or self.trigger_mode_override not in {"SENSOR", "HYBRID"}:
            return None
        value = self.sensor_threshold_edit.text().strip()
        return value or None

    @property
    def sensor_direction_override(self) -> str | None:
        if self.trigger_scope != "TASK_OVERRIDE" or self.trigger_mode_override not in {"SENSOR", "HYBRID"}:
            return None
        value = self.sensor_direction_combo.currentData()
        return str(value).strip().upper() if value else None

    @property
    def estimated_minutes_override(self) -> int | None:
        value = int(self.estimated_minutes_spin.value())
        return value or None

    @property
    def default_assigned_team_id(self) -> str:
        return self.default_assigned_team_edit.text().strip()

    @property
    def notes(self) -> str:
        return self.notes_edit.toPlainText().strip()

    @property
    def is_mandatory(self) -> bool:
        return self.is_mandatory_check.isChecked()


__all__ = [
    "MaintenancePreventivePlanEditDialog",
    "MaintenancePreventivePlanTaskEditDialog",
]
