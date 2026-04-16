from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from core.modules.maintenance_management import (
    MaintenanceAssetComponentService,
    MaintenanceAssetService,
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
    MaintenanceSensorService,
    MaintenanceSystemService,
    MaintenanceTaskTemplateService,
)
from core.modules.maintenance_management.domain import (
    MaintenancePlanStatus,
    MaintenancePlanType,
    MaintenanceTriggerMode,
)
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org import SiteService
from ui.modules.maintenance_management.preventive_library.detail_dialog import (
    MaintenancePreventivePlanLibraryDetailDialog,
)
from ui.modules.maintenance_management.preventive_library.edit_dialogs import (
    MaintenancePreventivePlanEditDialog,
)
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
    make_accent_badge,
    make_filter_toggle_button,
    make_meta_badge,
    reset_combo_options,
    selected_combo_value,
    set_filter_panel_visible,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenancePreventivePlanLibraryTab(QWidget):
    def __init__(
        self,
        *,
        preventive_plan_service: MaintenancePreventivePlanService,
        preventive_plan_task_service: MaintenancePreventivePlanTaskService,
        site_service: SiteService,
        asset_service: MaintenanceAssetService,
        component_service: MaintenanceAssetComponentService,
        system_service: MaintenanceSystemService,
        sensor_service: MaintenanceSensorService,
        task_template_service: MaintenanceTaskTemplateService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._preventive_plan_service = preventive_plan_service
        self._preventive_plan_task_service = preventive_plan_task_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._component_service = component_service
        self._system_service = system_service
        self._sensor_service = sensor_service
        self._task_template_service = task_template_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(user_session, "maintenance.manage")
        self._rows = []
        self._all_assets = []
        self._all_components = []
        self._all_systems = []
        self._all_sensors = []
        self._all_task_templates = []
        self._site_labels: dict[str, str] = {}
        self._asset_labels: dict[str, str] = {}
        self._component_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
        self._sensor_labels: dict[str, str] = {}
        self._task_template_labels: dict[str, str] = {}
        self._detail_dialog: MaintenancePreventivePlanLibraryDetailDialog | None = None
        self._setup_ui()
        self.reload_data()
        domain_events.domain_changed.connect(self._on_domain_change)
        domain_events.modules_changed.connect(self._on_modules_changed)
        domain_events.organizations_changed.connect(self._on_organization_changed)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self.context_badge = make_accent_badge("Context: -")
        self.plan_count_badge = make_meta_badge("0 plans")
        self.active_badge = make_meta_badge("0 active")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenancePreventiveLibraryHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Preventive Plan Library",
            subtitle_text="Author preventive-plan libraries and open the detail popup to manage the selected plan's reusable task stack.",
            badges=(self.context_badge, self.plan_count_badge, self.active_badge, self.access_badge),
        )

        actions, actions_layout = build_admin_surface_card(
            object_name="maintenancePreventiveLibraryActionSurface",
            alt=False,
        )
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_plan = QPushButton("New Plan")
        self.btn_edit_plan = QPushButton("Edit Plan")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_open_detail = QPushButton("Open Detail")
        for button, variant in (
            (self.btn_new_plan, "primary"),
            (self.btn_edit_plan, "secondary"),
            (self.btn_toggle_active, "secondary"),
            (self.btn_open_detail, "secondary"),
        ):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style(variant))
            action_row.addWidget(button)
        action_row.addStretch(1)
        actions_layout.addLayout(action_row)
        root.addWidget(actions)

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenancePreventiveLibraryControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All assets | All systems | Active only | All statuses | All plan types | All triggers")
        self.filter_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.filter_summary.setWordWrap(True)
        toolbar_row.addWidget(self.filter_summary, 1)
        self.btn_filters = make_filter_toggle_button(self)
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_refresh.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        toolbar_row.addWidget(self.btn_filters)
        toolbar_row.addWidget(self.btn_refresh)
        controls_layout.addLayout(toolbar_row)

        self.filter_panel = QWidget()
        filter_row = QHBoxLayout(self.filter_panel)
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(CFG.SPACING_MD)
        self.site_combo = QComboBox()
        self.asset_combo = QComboBox()
        self.system_combo = QComboBox()
        self.active_combo = QComboBox()
        self.active_combo.addItem("Active only", True)
        self.active_combo.addItem("Inactive only", False)
        self.active_combo.addItem("All statuses", None)
        self.status_combo = QComboBox()
        self.plan_type_combo = QComboBox()
        self.trigger_mode_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, name, anchor, type, status, or trigger")
        self.status_combo.addItem("All plan statuses", None)
        for value in MaintenancePlanStatus:
            self.status_combo.addItem(value.value.title(), value.value)
        self.plan_type_combo.addItem("All plan types", None)
        for value in MaintenancePlanType:
            self.plan_type_combo.addItem(value.value.replace("_", " ").title(), value.value)
        self.trigger_mode_combo.addItem("All triggers", None)
        for value in MaintenanceTriggerMode:
            self.trigger_mode_combo.addItem(value.value.title(), value.value)
        for label, widget in (
            ("Site", self.site_combo),
            ("Asset", self.asset_combo),
            ("System", self.system_combo),
            ("Lifecycle", self.active_combo),
            ("Plan Status", self.status_combo),
            ("Plan Type", self.plan_type_combo),
            ("Trigger", self.trigger_mode_combo),
        ):
            filter_row.addWidget(QLabel(label))
            filter_row.addWidget(widget)
        filter_row.addWidget(QLabel("Search"))
        filter_row.addWidget(self.search_edit, 1)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Plans", "-", "Visible in current preventive-library filter", CFG.COLOR_ACCENT)
        self.active_card = KpiCard("Active", "-", "Ready for planner use", CFG.COLOR_SUCCESS)
        self.auto_work_order_card = KpiCard("Auto WO", "-", "Generate work orders directly", CFG.COLOR_WARNING)
        self.sensor_card = KpiCard("Sensor / Hybrid", "-", "Condition-based or hybrid coverage", CFG.COLOR_ACCENT)
        for card in (self.total_card, self.active_card, self.auto_work_order_card, self.sensor_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        panel, layout = build_admin_surface_card(
            object_name="maintenancePreventiveLibraryGridSurface",
            alt=False,
        )
        title = QLabel("Preventive Plan Authoring Queue")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel(
            "Create and maintain preventive master records here, then open the detail popup to manage attached plan tasks."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.selection_summary = QLabel(
            "Select a preventive plan, then click Open Detail to inspect metadata and manage plan tasks."
        )
        self.selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_summary.setWordWrap(True)
        layout.addWidget(self.selection_summary)
        self.table = build_admin_table(
            headers=("Code", "Name", "Anchor", "Type", "Trigger", "Status", "Active"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.table)
        root.addWidget(panel, 1)

        self.site_combo.currentIndexChanged.connect(self._on_site_changed)
        self.asset_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_rows)
        )
        self.system_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_rows)
        )
        self.active_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_rows)
        )
        self.status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_rows)
        )
        self.plan_type_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_rows)
        )
        self.trigger_mode_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_rows)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_rows)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.reload_data)
        )
        self.btn_new_plan.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.create_plan)
        )
        self.btn_edit_plan.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.edit_plan)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self.toggle_active)
        )
        self.btn_open_detail.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Library", callback=self._open_detail_dialog)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_plan, self.btn_edit_plan, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="maintenance.manage")
        self._sync_actions()

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        selected_asset_id = selected_combo_value(self.asset_combo)
        selected_system_id = selected_combo_value(self.system_combo)
        selected_plan_type = selected_combo_value(self.plan_type_combo)
        try:
            sites = self._site_service.list_sites(active_only=None)
            all_assets = self._asset_service.list_assets(active_only=None)
            all_components = self._component_service.list_components(active_only=None)
            all_systems = self._system_service.list_systems(active_only=None)
            all_sensors = self._sensor_service.list_sensors(active_only=None)
            all_task_templates = self._task_template_service.list_task_templates(active_only=None)
            all_plans = self._preventive_plan_service.list_preventive_plans(active_only=None)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plan Library", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plan Library", f"Failed to load preventive-library filters: {exc}")
            return

        self._all_assets = all_assets
        self._all_components = all_components
        self._all_systems = all_systems
        self._all_sensors = all_sensors
        self._all_task_templates = all_task_templates
        self._site_labels = {site.id: site.name for site in sites}
        self._asset_labels = {row.id: f"{row.asset_code} - {row.name}" for row in all_assets}
        self._system_labels = {row.id: f"{row.system_code} - {row.name}" for row in all_systems}
        self._sensor_labels = {row.id: f"{row.sensor_code} - {row.sensor_name}" for row in all_sensors}
        self._task_template_labels = {
            row.id: f"{row.task_template_code} - {row.name}" for row in all_task_templates
        }
        self._component_labels = {row.id: f"{row.component_code} - {row.name}" for row in all_components}

        assets_for_site = [row for row in all_assets if selected_site_id in (None, row.site_id)]
        systems_for_site = [row for row in all_systems if selected_site_id in (None, row.site_id)]
        plan_types = sorted({row.plan_type.value for row in all_plans})

        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{site.site_code} - {site.name}", site.id) for site in sites],
            selected_value=selected_site_id,
        )
        reset_combo_options(
            self.asset_combo,
            placeholder="All assets",
            options=[(self._asset_labels[row.id], row.id) for row in assets_for_site],
            selected_value=selected_asset_id,
        )
        reset_combo_options(
            self.system_combo,
            placeholder="All systems",
            options=[(self._system_labels[row.id], row.id) for row in systems_for_site],
            selected_value=selected_system_id,
        )
        reset_combo_options(
            self.plan_type_combo,
            placeholder="All plan types",
            options=[(value.replace("_", " ").title(), value) for value in plan_types],
            selected_value=selected_plan_type,
        )
        self.reload_rows()

    def reload_rows(self) -> None:
        selected_plan_id = self._selected_plan_id()
        try:
            rows = self._preventive_plan_service.search_preventive_plans(
                search_text=self.search_edit.text(),
                active_only=self.active_combo.currentData(),
                site_id=selected_combo_value(self.site_combo),
                asset_id=selected_combo_value(self.asset_combo),
                system_id=selected_combo_value(self.system_combo),
                status=selected_combo_value(self.status_combo),
                plan_type=selected_combo_value(self.plan_type_combo),
                trigger_mode=selected_combo_value(self.trigger_mode_combo),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plan Library", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plan Library", f"Failed to refresh preventive-library rows: {exc}")
            return

        self._rows = rows
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.plan_count_badge.setText(f"{len(rows)} plans")
        self.active_badge.setText(f"{sum(1 for row in rows if row.is_active)} active")
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.asset_combo.currentText()} | {self.system_combo.currentText()} | "
            f"{self.active_combo.currentText()} | {self.status_combo.currentText()} | {self.plan_type_combo.currentText()} | {self.trigger_mode_combo.currentText()}"
            + (f" | Search: {self.search_edit.text().strip()}" if self.search_edit.text().strip() else "")
        )
        self.total_card.set_value(str(len(rows)))
        self.active_card.set_value(str(sum(1 for row in rows if row.is_active)))
        self.auto_work_order_card.set_value(str(sum(1 for row in rows if row.auto_generate_work_order)))
        self.sensor_card.set_value(
            str(sum(1 for row in rows if row.trigger_mode in {MaintenanceTriggerMode.SENSOR, MaintenanceTriggerMode.HYBRID}))
        )
        self._populate_table(selected_plan_id=selected_plan_id)

    def create_plan(self) -> None:
        dialog = MaintenancePreventivePlanEditDialog(
            sites=self._site_service.list_sites(active_only=None),
            assets=self._all_assets,
            components=self._all_components,
            systems=self._all_systems,
            sensors=self._all_sensors,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                self._preventive_plan_service.create_preventive_plan(
                    site_id=dialog.site_id or "",
                    plan_code=dialog.plan_code,
                    name=dialog.name,
                    asset_id=dialog.asset_id,
                    component_id=dialog.component_id,
                    system_id=dialog.system_id,
                    description=dialog.description,
                    status=dialog.status,
                    plan_type=dialog.plan_type,
                    priority=dialog.priority,
                    trigger_mode=dialog.trigger_mode,
                    schedule_policy=getattr(dialog, "schedule_policy", "FIXED"),
                    calendar_frequency_unit=dialog.calendar_frequency_unit,
                    calendar_frequency_value=dialog.calendar_frequency_value,
                    generation_horizon_count=getattr(dialog, "generation_horizon_count", 13),
                    generation_lead_value=getattr(dialog, "generation_lead_value", 0),
                    generation_lead_unit=getattr(dialog, "generation_lead_unit", "DAYS"),
                    sensor_id=dialog.sensor_id,
                    sensor_threshold=dialog.sensor_threshold,
                    sensor_direction=dialog.sensor_direction,
                    sensor_reset_rule=dialog.sensor_reset_rule,
                    requires_shutdown=dialog.requires_shutdown,
                    approval_required=dialog.approval_required,
                    auto_generate_work_order=dialog.auto_generate_work_order,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Preventive Plan Library", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Preventive Plan Library", f"Failed to create preventive plan: {exc}")
                return
            break
        self.reload_data()

    def edit_plan(self) -> None:
        row = self._selected_plan()
        if row is None:
            QMessageBox.information(self, "Preventive Plan Library", "Select a preventive plan to edit.")
            return
        dialog = MaintenancePreventivePlanEditDialog(
            sites=self._site_service.list_sites(active_only=None),
            assets=self._all_assets,
            components=self._all_components,
            systems=self._all_systems,
            sensors=self._all_sensors,
            preventive_plan=row,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                self._preventive_plan_service.update_preventive_plan(
                    row.id,
                    site_id=dialog.site_id,
                    plan_code=dialog.plan_code,
                    name=dialog.name,
                    asset_id=dialog.asset_id or "",
                    component_id=dialog.component_id or "",
                    system_id=dialog.system_id or "",
                    description=dialog.description,
                    status=dialog.status,
                    plan_type=dialog.plan_type,
                    priority=dialog.priority,
                    trigger_mode=dialog.trigger_mode,
                    schedule_policy=getattr(dialog, "schedule_policy", row.schedule_policy.value),
                    calendar_frequency_unit=dialog.calendar_frequency_unit,
                    calendar_frequency_value=dialog.calendar_frequency_value,
                    generation_horizon_count=getattr(dialog, "generation_horizon_count", row.generation_horizon_count),
                    generation_lead_value=getattr(dialog, "generation_lead_value", row.generation_lead_value),
                    generation_lead_unit=getattr(dialog, "generation_lead_unit", row.generation_lead_unit.value),
                    sensor_id=dialog.sensor_id or "",
                    sensor_threshold=dialog.sensor_threshold,
                    sensor_direction=dialog.sensor_direction,
                    sensor_reset_rule=dialog.sensor_reset_rule,
                    requires_shutdown=dialog.requires_shutdown,
                    approval_required=dialog.approval_required,
                    auto_generate_work_order=dialog.auto_generate_work_order,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                    expected_version=row.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Preventive Plan Library", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Preventive Plan Library", str(exc))
                self.reload_data()
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Preventive Plan Library", f"Failed to update preventive plan: {exc}")
                return
            break
        self.reload_data()

    def toggle_active(self) -> None:
        row = self._selected_plan()
        if row is None:
            QMessageBox.information(self, "Preventive Plan Library", "Select a preventive plan to update.")
            return
        try:
            self._preventive_plan_service.update_preventive_plan(
                row.id,
                is_active=not row.is_active,
                expected_version=row.version,
            )
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Preventive Plan Library", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plan Library", f"Failed to update preventive plan: {exc}")
            return
        self.reload_data()

    def _populate_table(self, *, selected_plan_id: str | None) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, row in enumerate(self._rows):
            values = (
                row.plan_code,
                row.name,
                self._anchor_label(row),
                row.plan_type.value.replace("_", " ").title(),
                row.trigger_mode.value.title(),
                row.status.value.title(),
                "Yes" if row.is_active else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.table.setItem(row_index, column, item)
            if selected_plan_id and row.id == selected_plan_id:
                selected_row = row_index
        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self._sync_actions()

    def _selected_plan_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_plan(self):
        plan_id = self._selected_plan_id()
        if not plan_id:
            return None
        try:
            return self._preventive_plan_service.get_preventive_plan(plan_id)
        except Exception:  # noqa: BLE001
            return None

    def _open_detail_dialog(self) -> None:
        plan_id = self._selected_plan_id()
        if not plan_id:
            QMessageBox.information(self, "Preventive Plan Library", "Select a preventive plan to open its detail view.")
            return
        dialog = MaintenancePreventivePlanLibraryDetailDialog(
            preventive_plan_service=self._preventive_plan_service,
            preventive_plan_task_service=self._preventive_plan_task_service,
            site_labels=self._site_labels,
            asset_labels=self._asset_labels,
            component_labels=self._component_labels,
            system_labels=self._system_labels,
            sensor_labels=self._sensor_labels,
            task_template_labels=self._task_template_labels,
            task_template_options=sorted(((label, row_id) for row_id, label in self._task_template_labels.items()), key=lambda row: row[0]),
            can_manage=self._can_manage,
            parent=self,
        )
        dialog.load_plan(plan_id)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._detail_dialog = dialog

    def _sync_actions(self) -> None:
        row = self._selected_plan()
        if row is None:
            self.selection_summary.setText(
                "Select a preventive plan, then click Open Detail to inspect metadata and manage plan tasks."
            )
            self.btn_new_plan.setEnabled(self._can_manage)
            self.btn_edit_plan.setEnabled(False)
            self.btn_toggle_active.setEnabled(False)
            self.btn_open_detail.setEnabled(False)
            return
        task_count = len(self._preventive_plan_task_service.list_plan_tasks(plan_id=row.id))
        self.selection_summary.setText(
            f"Selected: {row.plan_code} | Status: {row.status.value.title()} | Trigger: {row.trigger_mode.value.title()} | Tasks: {task_count}"
        )
        self.btn_new_plan.setEnabled(self._can_manage)
        self.btn_edit_plan.setEnabled(self._can_manage)
        self.btn_toggle_active.setEnabled(self._can_manage)
        self.btn_open_detail.setEnabled(True)

    def _anchor_label(self, row) -> str:
        if row.asset_id:
            return self._asset_labels.get(row.asset_id, row.asset_id)
        if row.component_id:
            return self._component_labels.get(row.component_id, row.component_id)
        if row.system_id:
            return self._system_labels.get(row.system_id, row.system_id)
        return self._site_labels.get(row.site_id, row.site_id)

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _on_site_changed(self) -> None:
        self.reload_data()

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") == "maintenance_management":
            self.reload_data()

    def _on_modules_changed(self, _module_code: str) -> None:
        self.reload_data()

    def _on_organization_changed(self, _organization_id: str) -> None:
        self.reload_data()

    def _context_label(self) -> str:
        service = self._platform_runtime_application_service
        if service is None or not hasattr(service, "current_context_label"):
            return "-"
        return str(service.current_context_label())

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenancePreventivePlanLibraryTab"]
