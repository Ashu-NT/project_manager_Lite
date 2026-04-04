from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from PySide6.QtWidgets import QDialog, QLabel, QTableWidgetItem, QVBoxLayout, QWidget

from core.modules.maintenance_management import MaintenancePreventivePlanService, MaintenancePreventivePlanTaskService
from core.modules.maintenance_management.domain import (
    MaintenancePlanTaskTriggerScope,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceTriggerMode,
)
from ui.modules.maintenance_management.shared import MaintenanceWorkbenchNavigator, MaintenanceWorkbenchSection, format_timestamp
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


@dataclass(frozen=True)
class MaintenancePreventivePlanDetailContext:
    due_state: str
    due_reason: str
    generation_target: str
    selected_plan_task_ids: tuple[str, ...]
    blocked_plan_task_ids: tuple[str, ...]
    is_due_soon: bool


class MaintenancePreventivePlanDetailDialog(QDialog):
    def __init__(
        self,
        *,
        preventive_plan_service: MaintenancePreventivePlanService,
        preventive_plan_task_service: MaintenancePreventivePlanTaskService,
        asset_labels: dict[str, str],
        system_labels: dict[str, str],
        sensor_labels: dict[str, str],
        task_template_labels: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._preventive_plan_service = preventive_plan_service
        self._preventive_plan_task_service = preventive_plan_task_service
        self._asset_labels = asset_labels
        self._system_labels = system_labels
        self._sensor_labels = sensor_labels
        self._task_template_labels = task_template_labels

        self.setWindowTitle("Preventive Plan Detail")
        self.resize(1060, 720)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.title_label = QLabel("No preventive plan selected")
        self.title_label.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        root.addWidget(self.title_label)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenancePreventiveDetailWorkbench", parent=self)
        self.overview_widget, self.overview_summary = self._build_overview_widget()
        self.tasks_widget, self.task_table = self._build_tasks_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(key="overview", label="Overview", widget=self.overview_widget),
                MaintenanceWorkbenchSection(key="plan_tasks", label="Plan Tasks", widget=self.tasks_widget),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

    def load_plan(self, plan_id: str, *, context: MaintenancePreventivePlanDetailContext) -> None:
        plan = self._preventive_plan_service.get_preventive_plan(plan_id)
        plan_tasks = sorted(
            self._preventive_plan_task_service.list_plan_tasks(plan_id=plan.id),
            key=lambda row: row.sequence_no,
        )
        self.title_label.setText(f"{plan.plan_code} - {plan.name}")
        self.overview_summary.setText(
            "\n".join(
                [
                    f"Anchor: {self._anchor_label(plan)}",
                    f"Type: {plan.plan_type.value.replace('_', ' ').title()} | Status: {plan.status.value.title()} | Priority: {plan.priority.value.title()}",
                    f"Trigger: {self._trigger_summary(plan)} | Target: {context.generation_target.replace('_', ' ').title()}",
                    f"Due state: {self._due_state_label(context)} | Reason: {context.due_reason or '-'}",
                    f"Last generated: {format_timestamp(plan.last_generated_at)} | Last completed: {format_timestamp(plan.last_completed_at)}",
                    f"Next due at: {format_timestamp(plan.next_due_at)} | Next counter: {plan.next_due_counter if plan.next_due_counter is not None else '-'}",
                    f"Controls: {'Shutdown required' if plan.requires_shutdown else 'No shutdown'} | {'Approval required' if plan.approval_required else 'No approval'}",
                    f"Notes: {plan.notes or '-'}",
                ]
            )
        )
        self._populate_task_table(plan_tasks, context=context)
        self.workbench.set_current_section("overview")

    def _populate_task_table(
        self,
        plan_tasks: list[MaintenancePreventivePlanTask],
        *,
        context: MaintenancePreventivePlanDetailContext,
    ) -> None:
        selected_ids = set(context.selected_plan_task_ids)
        blocked_ids = set(context.blocked_plan_task_ids)
        self.task_table.setRowCount(len(plan_tasks))
        for row_index, plan_task in enumerate(plan_tasks):
            values = (
                str(plan_task.sequence_no),
                self._task_template_labels.get(plan_task.task_template_id, plan_task.task_template_id),
                "Inherit plan" if plan_task.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN else "Task override",
                self._plan_task_trigger_summary(plan_task),
                self._plan_task_due_state(plan_task, context, selected_ids=selected_ids, blocked_ids=blocked_ids),
                str(plan_task.estimated_minutes_override or "-"),
            )
            for column, value in enumerate(values):
                self.task_table.setItem(row_index, column, QTableWidgetItem(value))

    def _build_overview_widget(self) -> tuple[QWidget, QLabel]:
        widget, layout = build_admin_surface_card(
            object_name="maintenancePreventiveDialogOverviewSurface",
            alt=False,
        )
        title = QLabel("Plan Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        summary = QLabel("Select a preventive plan to inspect trigger state and generation context.")
        summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)
        return widget, summary

    def _build_tasks_widget(self) -> tuple[QWidget, object]:
        widget, layout = build_admin_surface_card(
            object_name="maintenancePreventiveDialogTasksSurface",
            alt=False,
        )
        title = QLabel("Plan Tasks")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Task library entries and task-level trigger interpretation for the selected plan.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        table = build_admin_table(
            headers=("Sequence", "Task Template", "Trigger Scope", "Trigger Rule", "Due State", "Minutes"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(table)
        return widget, table

    def _anchor_label(self, plan: MaintenancePreventivePlan) -> str:
        if plan.asset_id:
            return self._asset_labels.get(plan.asset_id, plan.asset_id)
        if plan.system_id:
            return self._system_labels.get(plan.system_id, plan.system_id)
        if plan.component_id:
            return plan.component_id
        return plan.site_id

    def _trigger_summary(self, plan: MaintenancePreventivePlan) -> str:
        if plan.trigger_mode == MaintenanceTriggerMode.CALENDAR:
            return self._calendar_rule_label(plan.calendar_frequency_unit, plan.calendar_frequency_value)
        if plan.trigger_mode == MaintenanceTriggerMode.SENSOR:
            return self._sensor_rule_label(plan.sensor_id, plan.sensor_threshold, plan.sensor_direction)
        return (
            f"{self._calendar_rule_label(plan.calendar_frequency_unit, plan.calendar_frequency_value)} + "
            f"{self._sensor_rule_label(plan.sensor_id, plan.sensor_threshold, plan.sensor_direction)}"
        )

    def _plan_task_trigger_summary(self, plan_task: MaintenancePreventivePlanTask) -> str:
        if plan_task.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
            return "Uses plan trigger"
        if plan_task.trigger_mode_override == MaintenanceTriggerMode.CALENDAR:
            return self._calendar_rule_label(
                plan_task.calendar_frequency_unit_override,
                plan_task.calendar_frequency_value_override,
            )
        if plan_task.trigger_mode_override == MaintenanceTriggerMode.SENSOR:
            return self._sensor_rule_label(
                plan_task.sensor_id_override,
                plan_task.sensor_threshold_override,
                plan_task.sensor_direction_override,
            )
        return (
            f"{self._calendar_rule_label(plan_task.calendar_frequency_unit_override, plan_task.calendar_frequency_value_override)} + "
            f"{self._sensor_rule_label(plan_task.sensor_id_override, plan_task.sensor_threshold_override, plan_task.sensor_direction_override)}"
        )

    def _plan_task_due_state(
        self,
        plan_task: MaintenancePreventivePlanTask,
        context: MaintenancePreventivePlanDetailContext,
        *,
        selected_ids: set[str],
        blocked_ids: set[str],
    ) -> str:
        if context.due_state == "INACTIVE":
            return "Inactive"
        if plan_task.id in selected_ids:
            return "Due"
        if plan_task.id in blocked_ids:
            return "Blocked"
        if plan_task.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
            return "Plan state"
        return "Idle"

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

    @staticmethod
    def _due_state_label(context: MaintenancePreventivePlanDetailContext) -> str:
        if context.is_due_soon and context.due_state == "NOT_DUE":
            return "Due Soon"
        return context.due_state.replace("_", " ").title()

    @staticmethod
    def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenancePreventivePlanDetailContext", "MaintenancePreventivePlanDetailDialog"]
