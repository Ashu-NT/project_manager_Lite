from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.modules.maintenance_management import (
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
)
from core.modules.maintenance_management.domain import (
    MaintenancePlanTaskTriggerScope,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceTriggerMode,
)
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from ui.modules.maintenance_management.preventive_library.edit_dialogs import (
    MaintenancePreventivePlanTaskEditDialog,
)
from ui.modules.maintenance_management.shared import (
    MaintenanceWorkbenchNavigator,
    MaintenanceWorkbenchSection,
    build_maintenance_header,
    format_timestamp,
    make_accent_badge,
    make_meta_badge,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from src.ui.platform.widgets.admin_surface import build_admin_surface_card, build_admin_table
from src.ui.shared.widgets.guards import apply_permission_hint, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class MaintenancePreventivePlanLibraryDetailDialog(QDialog):
    def __init__(
        self,
        *,
        preventive_plan_service: MaintenancePreventivePlanService,
        preventive_plan_task_service: MaintenancePreventivePlanTaskService,
        site_labels: dict[str, str],
        asset_labels: dict[str, str],
        component_labels: dict[str, str],
        system_labels: dict[str, str],
        sensor_labels: dict[str, str],
        task_template_labels: dict[str, str],
        task_template_options: list[tuple[str, str]],
        can_manage: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._preventive_plan_service = preventive_plan_service
        self._preventive_plan_task_service = preventive_plan_task_service
        self._site_labels = site_labels
        self._asset_labels = asset_labels
        self._component_labels = component_labels
        self._system_labels = system_labels
        self._sensor_labels = sensor_labels
        self._task_template_labels = task_template_labels
        self._task_template_options = task_template_options
        self._can_manage = can_manage
        self._current_plan_id: str | None = None
        self._current_plan: MaintenancePreventivePlan | None = None
        self._task_rows: list[MaintenancePreventivePlanTask] = []

        self.setWindowTitle("Preventive Plan Library Detail")
        self.resize(1160, 780)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.context_badge = make_accent_badge("Plan")
        self.task_count_badge = make_meta_badge("0 plan tasks")
        self.active_badge = make_meta_badge("Inactive")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenancePreventiveLibraryDetailHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Preventive Plan Library Detail",
            subtitle_text="Inspect preventive metadata and manage the task library that will drive generated work.",
            badges=(self.context_badge, self.task_count_badge, self.active_badge, self.access_badge),
        )

        self.workbench = MaintenanceWorkbenchNavigator(
            object_name="maintenancePreventiveLibraryDetailWorkbench",
            parent=self,
        )
        self.overview_widget = self._build_overview_widget()
        self.tasks_widget = self._build_tasks_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(key="overview", label="Overview", widget=self.overview_widget),
                MaintenanceWorkbenchSection(key="plan_tasks", label="Plan Tasks", widget=self.tasks_widget),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

        self.task_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Preventive Plan Library Detail", callback=self._sync_task_actions)
        )
        self.btn_new_plan_task.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Library Detail", callback=self._create_plan_task)
        )
        self.btn_edit_plan_task.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Library Detail", callback=self._edit_plan_task)
        )
        apply_permission_hint(self.btn_new_plan_task, allowed=self._can_manage, missing_permission="maintenance.manage")
        apply_permission_hint(self.btn_edit_plan_task, allowed=self._can_manage, missing_permission="maintenance.manage")
        domain_events.domain_changed.connect(self._on_domain_change)
        self._sync_task_actions()

    def _build_overview_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenancePreventiveLibraryDetailOverviewSurface",
            alt=False,
        )
        title = QLabel("Plan Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel(
            "Anchor, trigger strategy, generation rules, and planner-facing metadata for the selected preventive library entry."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        overview_grid = QGridLayout()
        overview_grid.setHorizontalSpacing(CFG.SPACING_MD)
        overview_grid.setVerticalSpacing(CFG.SPACING_SM)
        self.overview_labels: dict[str, QLabel] = {}
        fields = (
            ("Code", "code"),
            ("Name", "name"),
            ("Site", "site"),
            ("Anchor", "anchor"),
            ("Status", "status"),
            ("Type", "type"),
            ("Priority", "priority"),
            ("Trigger", "trigger"),
            ("Next Due", "next_due"),
            ("Last Generated", "last_generated"),
            ("Last Completed", "last_completed"),
            ("Controls", "controls"),
            ("Created", "created_at"),
            ("Updated", "updated_at"),
        )
        for index, (label, key) in enumerate(fields):
            value_label = QLabel("-")
            value_label.setWordWrap(True)
            self.overview_labels[key] = value_label
            overview_grid.addWidget(QLabel(label), index, 0, Qt.AlignTop)
            overview_grid.addWidget(value_label, index, 1)
        layout.addLayout(overview_grid)

        self.description_label = QLabel("-")
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.notes_label = QLabel("-")
        self.notes_label.setWordWrap(True)
        self.notes_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        layout.addWidget(QLabel("Description"))
        layout.addWidget(self.description_label)
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.notes_label)
        return widget

    def _build_tasks_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenancePreventiveLibraryDetailTasksSurface",
            alt=False,
        )
        title = QLabel("Plan Tasks")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Attach reusable task templates to this plan and define task-level trigger overrides when needed.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.task_summary = QLabel("Select a plan task to edit it.")
        self.task_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.task_summary.setWordWrap(True)
        layout.addWidget(self.task_summary)
        self.task_table = build_admin_table(
            headers=("Sequence", "Task Template", "Trigger Scope", "Trigger Rule", "Mandatory", "Minutes"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.task_table)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_plan_task = QPushButton("New Plan Task")
        self.btn_edit_plan_task = QPushButton("Edit Plan Task")
        for button in (self.btn_new_plan_task, self.btn_edit_plan_task):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
            action_row.addWidget(button)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        return widget

    def load_plan(self, plan_id: str, *, selected_plan_task_id: str | None = None) -> None:
        self._current_plan_id = plan_id
        try:
            plan = self._preventive_plan_service.get_preventive_plan(plan_id)
            task_rows = sorted(
                self._preventive_plan_task_service.list_plan_tasks(plan_id=plan.id),
                key=lambda row: row.sequence_no,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plan Library Detail", str(exc))
            return
        except NotFoundError as exc:
            QMessageBox.warning(self, "Preventive Plan Library Detail", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plan Library Detail", f"Failed to load preventive plan detail: {exc}")
            return

        self._current_plan = plan
        self._task_rows = task_rows
        self.context_badge.setText(f"Plan: {plan.plan_code}")
        self.task_count_badge.setText(f"{len(task_rows)} plan tasks")
        self.active_badge.setText("Active" if plan.is_active else "Inactive")
        self.setWindowTitle(f"Preventive Plan Library Detail - {plan.plan_code}")
        self._populate_overview(plan)
        self._populate_task_table(selected_plan_task_id=selected_plan_task_id)
        self.workbench.set_current_section("overview")

    def _populate_overview(self, plan: MaintenancePreventivePlan) -> None:
        self.overview_labels["code"].setText(plan.plan_code)
        self.overview_labels["name"].setText(plan.name)
        self.overview_labels["site"].setText(self._site_labels.get(plan.site_id, plan.site_id))
        self.overview_labels["anchor"].setText(self._anchor_label(plan))
        self.overview_labels["status"].setText(plan.status.value.title())
        self.overview_labels["type"].setText(plan.plan_type.value.replace("_", " ").title())
        self.overview_labels["priority"].setText(plan.priority.value.title())
        self.overview_labels["trigger"].setText(self._trigger_summary(plan))
        self.overview_labels["next_due"].setText(
            format_timestamp(plan.next_due_at)
            if plan.next_due_at is not None
            else (str(plan.next_due_counter) if plan.next_due_counter is not None else "-")
        )
        self.overview_labels["last_generated"].setText(format_timestamp(plan.last_generated_at))
        self.overview_labels["last_completed"].setText(format_timestamp(plan.last_completed_at))
        self.overview_labels["controls"].setText(
            " | ".join(
                [
                    "Shutdown required" if plan.requires_shutdown else "No shutdown",
                    "Approval required" if plan.approval_required else "No approval",
                    "Auto-generate WO" if plan.auto_generate_work_order else "Generate WR/queue",
                    f"Schedule {plan.schedule_policy.value.title()}",
                    f"Horizon {plan.generation_horizon_count}",
                    (
                        f"Lead {plan.generation_lead_value} {plan.generation_lead_unit.value.title()}"
                        if plan.generation_lead_value > 0
                        else "Lead On due date"
                    ),
                ]
            )
        )
        self.overview_labels["created_at"].setText(format_timestamp(plan.created_at))
        self.overview_labels["updated_at"].setText(format_timestamp(plan.updated_at))
        self.description_label.setText(plan.description or "-")
        self.notes_label.setText(plan.notes or "-")

    def _populate_task_table(self, *, selected_plan_task_id: str | None) -> None:
        self.task_table.blockSignals(True)
        self.task_table.setRowCount(len(self._task_rows))
        selected_row = -1
        for row_index, row in enumerate(self._task_rows):
            values = (
                str(row.sequence_no),
                self._task_template_labels.get(row.task_template_id, row.task_template_id),
                row.trigger_scope.value.replace("_", " ").title(),
                self._plan_task_trigger_summary(row),
                "Yes" if row.is_mandatory else "No",
                str(row.estimated_minutes_override) if row.estimated_minutes_override is not None else "-",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.task_table.setItem(row_index, column, item)
            if selected_plan_task_id and row.id == selected_plan_task_id:
                selected_row = row_index
        self.task_table.blockSignals(False)
        if selected_row >= 0:
            self.task_table.selectRow(selected_row)
        else:
            self.task_table.clearSelection()
        self._sync_task_actions()

    def _create_plan_task(self) -> None:
        plan = self._current_plan
        if plan is None:
            return
        dialog = MaintenancePreventivePlanTaskEditDialog(
            task_template_options=self._task_template_options,
            sensor_options=self._sensor_options_for_plan(plan),
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                row = self._preventive_plan_task_service.create_plan_task(
                    plan_id=plan.id,
                    task_template_id=dialog.task_template_id or "",
                    trigger_scope=dialog.trigger_scope,
                    trigger_mode_override=dialog.trigger_mode_override,
                    calendar_frequency_unit_override=dialog.calendar_frequency_unit_override,
                    calendar_frequency_value_override=dialog.calendar_frequency_value_override,
                    sensor_id_override=dialog.sensor_id_override,
                    sensor_threshold_override=dialog.sensor_threshold_override,
                    sensor_direction_override=dialog.sensor_direction_override,
                    sequence_no=dialog.sequence_no,
                    is_mandatory=dialog.is_mandatory,
                    default_assigned_team_id=dialog.default_assigned_team_id,
                    estimated_minutes_override=dialog.estimated_minutes_override,
                    notes=dialog.notes,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Preventive Plan Library Detail", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Preventive Plan Library Detail", f"Failed to create plan task: {exc}")
                return
            self.load_plan(plan.id, selected_plan_task_id=row.id)
            self.workbench.set_current_section("plan_tasks")
            return

    def _edit_plan_task(self) -> None:
        plan = self._current_plan
        row = self._selected_plan_task()
        if plan is None or row is None:
            QMessageBox.information(self, "Preventive Plan Library Detail", "Select a plan task to edit.")
            return
        dialog = MaintenancePreventivePlanTaskEditDialog(
            task_template_options=self._task_template_options,
            sensor_options=self._sensor_options_for_plan(plan),
            plan_task=row,
            parent=self,
        )
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                updated = self._preventive_plan_task_service.update_plan_task(
                    row.id,
                    task_template_id=dialog.task_template_id or "",
                    trigger_scope=dialog.trigger_scope,
                    trigger_mode_override=dialog.trigger_mode_override,
                    calendar_frequency_unit_override=dialog.calendar_frequency_unit_override,
                    calendar_frequency_value_override=dialog.calendar_frequency_value_override,
                    sensor_id_override=dialog.sensor_id_override,
                    sensor_threshold_override=dialog.sensor_threshold_override,
                    sensor_direction_override=dialog.sensor_direction_override,
                    sequence_no=dialog.sequence_no,
                    is_mandatory=dialog.is_mandatory,
                    default_assigned_team_id=dialog.default_assigned_team_id,
                    estimated_minutes_override=dialog.estimated_minutes_override,
                    notes=dialog.notes,
                    expected_version=row.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Preventive Plan Library Detail", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Preventive Plan Library Detail", str(exc))
                self.load_plan(plan.id, selected_plan_task_id=row.id)
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Preventive Plan Library Detail", f"Failed to update plan task: {exc}")
                return
            self.load_plan(plan.id, selected_plan_task_id=updated.id)
            self.workbench.set_current_section("plan_tasks")
            return

    def _selected_plan_task_id(self) -> str | None:
        row = self.task_table.currentRow()
        if row < 0:
            return None
        item = self.task_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_plan_task(self) -> MaintenancePreventivePlanTask | None:
        selected_id = self._selected_plan_task_id()
        if not selected_id:
            return None
        return next((row for row in self._task_rows if row.id == selected_id), None)

    def _sync_task_actions(self) -> None:
        row = self._selected_plan_task()
        if row is None:
            self.task_summary.setText("Select a plan task to edit it.")
            self.btn_new_plan_task.setEnabled(self._can_manage)
            self.btn_edit_plan_task.setEnabled(False)
            return
        self.task_summary.setText(
            f"Selected: {row.sequence_no} | Template: {self._task_template_labels.get(row.task_template_id, row.task_template_id)} | Scope: {row.trigger_scope.value.replace('_', ' ').title()}"
        )
        self.btn_new_plan_task.setEnabled(self._can_manage)
        self.btn_edit_plan_task.setEnabled(self._can_manage)

    def _anchor_label(self, plan: MaintenancePreventivePlan) -> str:
        if plan.asset_id:
            return self._asset_labels.get(plan.asset_id, plan.asset_id)
        if plan.component_id:
            return self._component_labels.get(plan.component_id, plan.component_id)
        if plan.system_id:
            return self._system_labels.get(plan.system_id, plan.system_id)
        return self._site_labels.get(plan.site_id, plan.site_id)

    def _trigger_summary(self, plan: MaintenancePreventivePlan) -> str:
        if plan.trigger_mode == MaintenanceTriggerMode.CALENDAR:
            return self._calendar_rule_label(plan.calendar_frequency_unit, plan.calendar_frequency_value)
        if plan.trigger_mode == MaintenanceTriggerMode.SENSOR:
            return self._sensor_rule_label(plan.sensor_id, plan.sensor_threshold, plan.sensor_direction)
        return (
            f"{self._calendar_rule_label(plan.calendar_frequency_unit, plan.calendar_frequency_value)} + "
            f"{self._sensor_rule_label(plan.sensor_id, plan.sensor_threshold, plan.sensor_direction)}"
        )

    def _plan_task_trigger_summary(self, row: MaintenancePreventivePlanTask) -> str:
        if row.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
            return "Uses plan trigger"
        if row.trigger_mode_override == MaintenanceTriggerMode.CALENDAR:
            return self._calendar_rule_label(row.calendar_frequency_unit_override, row.calendar_frequency_value_override)
        if row.trigger_mode_override == MaintenanceTriggerMode.SENSOR:
            return self._sensor_rule_label(row.sensor_id_override, row.sensor_threshold_override, row.sensor_direction_override)
        return (
            f"{self._calendar_rule_label(row.calendar_frequency_unit_override, row.calendar_frequency_value_override)} + "
            f"{self._sensor_rule_label(row.sensor_id_override, row.sensor_threshold_override, row.sensor_direction_override)}"
        )

    def _sensor_options_for_plan(self, _plan: MaintenancePreventivePlan) -> list[tuple[str, str]]:
        return sorted(((label, sensor_id) for sensor_id, label in self._sensor_labels.items()), key=lambda row: row[0])

    @staticmethod
    def _calendar_rule_label(unit, value: int | None) -> str:
        if unit is None or value in (None, 0):
            return "No calendar rule"
        return f"Every {value} {unit.value.replace('_', ' ').lower()}"

    def _sensor_rule_label(self, sensor_id: str | None, threshold, direction) -> str:
        if not sensor_id or threshold is None or direction is None:
            return "No sensor rule"
        sensor_label = self._sensor_labels.get(sensor_id, sensor_id)
        direction_label = direction.value.replace("_", " ").lower()
        return f"{sensor_label} {direction_label} {threshold}"

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") != "maintenance_management":
            return
        if self._current_plan_id is None:
            return
        if event.entity_type not in {"maintenance_preventive_plan", "maintenance_preventive_plan_task"}:
            return
        self.load_plan(self._current_plan_id, selected_plan_task_id=self._selected_plan_task_id())

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenancePreventivePlanLibraryDetailDialog"]
