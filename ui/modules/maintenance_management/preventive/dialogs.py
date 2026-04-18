from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidgetItem, QVBoxLayout, QWidget

from core.modules.maintenance_management import (
    MaintenancePreventiveGenerationService,
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
)
from core.modules.maintenance_management.domain import (
    MaintenancePlanTaskTriggerScope,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceTriggerMode,
)
from src.core.platform.common.exceptions import BusinessRuleError
from ui.modules.maintenance_management.shared import MaintenanceWorkbenchNavigator, MaintenanceWorkbenchSection, format_timestamp
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from src.ui.shared.widgets.guards import make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


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
        preventive_generation_service: MaintenancePreventiveGenerationService,
        preventive_plan_service: MaintenancePreventivePlanService,
        preventive_plan_task_service: MaintenancePreventivePlanTaskService,
        asset_labels: dict[str, str],
        system_labels: dict[str, str],
        sensor_labels: dict[str, str],
        task_template_labels: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._preventive_generation_service = preventive_generation_service
        self._preventive_plan_service = preventive_plan_service
        self._preventive_plan_task_service = preventive_plan_task_service
        self._asset_labels = asset_labels
        self._system_labels = system_labels
        self._sensor_labels = sensor_labels
        self._task_template_labels = task_template_labels
        self._current_plan_id: str | None = None
        self._current_context: MaintenancePreventivePlanDetailContext | None = None

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
        self.forecast_widget, self.forecast_summary, self.forecast_table = self._build_forecast_widget()
        self.tasks_widget, self.task_table = self._build_tasks_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(key="overview", label="Overview", widget=self.overview_widget),
                MaintenanceWorkbenchSection(key="forecast", label="Forecast", widget=self.forecast_widget),
                MaintenanceWorkbenchSection(key="plan_tasks", label="Plan Tasks", widget=self.tasks_widget),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

        self.btn_refresh_forecast.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Detail", callback=self._refresh_forecast)
        )
        self.btn_generate_due_work.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Detail", callback=self._generate_due_work)
        )
        self.btn_regenerate_horizon.clicked.connect(
            make_guarded_slot(self, title="Preventive Plan Detail", callback=self._regenerate_horizon)
        )

    def load_plan(self, plan_id: str, *, context: MaintenancePreventivePlanDetailContext) -> None:
        self._current_plan_id = plan_id
        self._current_context = context
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
        self._populate_forecast_table(plan)
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

    def _build_forecast_widget(self) -> tuple[QWidget, QLabel, object]:
        widget, layout = build_admin_surface_card(
            object_name="maintenancePreventiveDialogForecastSurface",
            alt=False,
        )
        title = QLabel("Forecast")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Future schedule instances, generation windows, and planner-facing regeneration controls.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        summary = QLabel("Select a preventive plan to preview its schedule horizon.")
        summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        summary.setWordWrap(True)
        layout.addWidget(summary)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_refresh_forecast = QPushButton("Refresh Forecast")
        self.btn_generate_due_work = QPushButton("Generate Due Work")
        self.btn_regenerate_horizon = QPushButton("Regenerate Horizon")
        for button in (self.btn_refresh_forecast, self.btn_generate_due_work, self.btn_regenerate_horizon):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
        action_row.addWidget(self.btn_refresh_forecast)
        action_row.addWidget(self.btn_generate_due_work)
        action_row.addWidget(self.btn_regenerate_horizon)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        table = build_admin_table(
            headers=("Due", "Window Opens", "Instance", "Planner State", "Generated Work", "Completed"),
            resize_modes=(
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(table)
        return widget, summary, table

    def _populate_forecast_table(self, plan: MaintenancePreventivePlan) -> None:
        rows = self._preventive_generation_service.preview_plan_schedule(plan_id=plan.id)
        self.forecast_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            generated_work = row.generated_work_order_id or row.generated_work_request_id or "-"
            values = (
                format_timestamp(row.due_at),
                format_timestamp(row.generation_window_opens_at),
                row.instance_status.replace("_", " ").title(),
                row.planner_state.replace("_", " ").title(),
                generated_work,
                format_timestamp(row.completed_at),
            )
            for column, value in enumerate(values):
                self.forecast_table.setItem(row_index, column, QTableWidgetItem(value))
        if not rows:
            self.forecast_summary.setText(
                "No persisted forecast rows are available for this plan yet. Sensor-only plans can still show due state in Overview."
            )
            return
        first_row = rows[0]
        self.forecast_summary.setText(
            f"{len(rows)} instance(s) in horizon. Next Window opens {format_timestamp(first_row.generation_window_opens_at)} "
            f"for due date {format_timestamp(first_row.due_at)}."
        )

    def _refresh_forecast(self) -> None:
        if not self._current_plan_id or self._current_context is None:
            return
        try:
            self.load_plan(self._current_plan_id, context=self._reload_context(self._current_plan_id))
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plan Detail", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plan Detail", f"Failed to refresh preventive forecast: {exc}")

    def _regenerate_horizon(self) -> None:
        if not self._current_plan_id or self._current_context is None:
            return
        try:
            self._preventive_generation_service.regenerate_plan_schedule(plan_id=self._current_plan_id)
            self.load_plan(self._current_plan_id, context=self._reload_context(self._current_plan_id))
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plan Detail", str(exc))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plan Detail", f"Failed to regenerate preventive horizon: {exc}")

    def _generate_due_work(self) -> None:
        if not self._current_plan_id or self._current_context is None:
            return
        try:
            results = self._preventive_generation_service.generate_due_work(plan_id=self._current_plan_id)
            result = results[0] if results else None
            self.load_plan(self._current_plan_id, context=self._reload_context(self._current_plan_id))
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plan Detail", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plan Detail", f"Failed to generate preventive work: {exc}")
            return
        if result is None:
            QMessageBox.information(self, "Preventive Plan Detail", "No preventive generation result was returned.")
        elif result.generated_work_order_id or result.generated_work_request_id:
            generated_label = result.generated_work_order_id or result.generated_work_request_id
            QMessageBox.information(
                self,
                "Preventive Plan Detail",
                f"Generated preventive work successfully.\nReference: {generated_label}",
            )
        elif result.skipped_reason:
            QMessageBox.information(
                self,
                "Preventive Plan Detail",
                f"No work was generated.\nReason: {result.skipped_reason}",
            )

    def _reload_context(self, plan_id: str) -> MaintenancePreventivePlanDetailContext:
        plan = self._preventive_plan_service.get_preventive_plan(plan_id)
        candidate_rows = self._preventive_generation_service.list_due_candidates(plan_id=plan_id)
        candidate = candidate_rows[0] if candidate_rows else None
        next_due = self._ensure_utc_datetime(plan.next_due_at)
        now = datetime.now(timezone.utc)
        is_due_soon = (
            candidate is None
            and plan.is_active
            and plan.status.value == "ACTIVE"
            and next_due is not None
            and now <= next_due <= now + timedelta(days=30)
        )
        if candidate is None:
            return MaintenancePreventivePlanDetailContext(
                due_state="INACTIVE" if (not plan.is_active or plan.status.value != "ACTIVE") else "NOT_DUE",
                due_reason=(
                    "Preventive plan is not active for due generation."
                    if (not plan.is_active or plan.status.value != "ACTIVE")
                    else "Preventive plan is active but has no current due candidate."
                ),
                generation_target="WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST",
                selected_plan_task_ids=(),
                blocked_plan_task_ids=(),
                is_due_soon=is_due_soon,
            )
        return MaintenancePreventivePlanDetailContext(
            due_state=candidate.due_state,
            due_reason=candidate.due_reason,
            generation_target=candidate.generation_target,
            selected_plan_task_ids=candidate.selected_plan_task_ids,
            blocked_plan_task_ids=candidate.blocked_plan_task_ids,
            is_due_soon=False,
        )

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
