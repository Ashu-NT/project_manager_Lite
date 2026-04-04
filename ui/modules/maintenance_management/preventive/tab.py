from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from application.platform import PlatformRuntimeApplicationService
from core.modules.maintenance_management import (
    MaintenanceAssetService,
    MaintenancePreventiveGenerationService,
    MaintenancePreventivePlanService,
    MaintenancePreventivePlanTaskService,
    MaintenanceSensorService,
    MaintenanceSystemService,
    MaintenanceTaskTemplateService,
)
from core.modules.maintenance_management.domain import (
    MaintenancePlanStatus,
    MaintenancePlanTaskTriggerScope,
    MaintenancePlanType,
    MaintenancePreventivePlan,
    MaintenancePreventivePlanTask,
    MaintenanceTriggerMode,
)
from core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from core.platform.org import SiteService
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
    format_timestamp,
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
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


_DUE_STATE_ALL = "__ALL__"
_DUE_STATE_DUE = "DUE"
_DUE_STATE_DUE_SOON = "DUE_SOON"
_DUE_STATE_BLOCKED = "BLOCKED"
_DUE_STATE_NOT_DUE = "NOT_DUE"
_DUE_STATE_INACTIVE = "INACTIVE"
_DUE_SOON_WINDOW = timedelta(days=30)


@dataclass(frozen=True)
class _PreventivePlanRow:
    plan: MaintenancePreventivePlan
    due_state: str
    due_reason: str
    generation_target: str
    selected_plan_task_ids: tuple[str, ...]
    blocked_plan_task_ids: tuple[str, ...]
    is_due_soon: bool


class MaintenancePreventivePlansTab(QWidget):
    def __init__(
        self,
        *,
        preventive_plan_service: MaintenancePreventivePlanService,
        preventive_plan_task_service: MaintenancePreventivePlanTaskService,
        preventive_generation_service: MaintenancePreventiveGenerationService,
        site_service: SiteService,
        asset_service: MaintenanceAssetService,
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
        self._preventive_generation_service = preventive_generation_service
        self._site_service = site_service
        self._asset_service = asset_service
        self._system_service = system_service
        self._sensor_service = sensor_service
        self._task_template_service = task_template_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._site_labels: dict[str, str] = {}
        self._asset_labels: dict[str, str] = {}
        self._system_labels: dict[str, str] = {}
        self._sensor_labels: dict[str, str] = {}
        self._task_template_labels: dict[str, str] = {}
        self._visible_rows: list[_PreventivePlanRow] = []
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
        self.due_badge = make_meta_badge("0 due now")
        self.blocked_badge = make_meta_badge("0 blocked")
        build_maintenance_header(
            root=root,
            object_name="maintenancePreventiveHeaderCard",
            eyebrow_text="PREVENTIVE LIBRARY",
            title_text="Preventive Plans",
            subtitle_text="Review preventive libraries, due state, blocked hybrid triggers, and the task structure that will generate execution work.",
            badges=(self.context_badge, self.due_badge, self.blocked_badge),
        )

        controls, controls_layout = build_admin_surface_card(
            object_name="maintenancePreventiveControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: All sites | All due states | All statuses | All trigger modes")
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
        filter_row = QGridLayout(self.filter_panel)
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setHorizontalSpacing(CFG.SPACING_MD)
        filter_row.setVerticalSpacing(CFG.SPACING_SM)
        self.site_combo = QComboBox()
        self.due_state_combo = QComboBox()
        self.status_combo = QComboBox()
        self.plan_type_combo = QComboBox()
        self.trigger_mode_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by plan code, plan name, type, trigger, or due reason")

        self.due_state_combo.addItem("All due states", _DUE_STATE_ALL)
        self.due_state_combo.addItem("Due now", _DUE_STATE_DUE)
        self.due_state_combo.addItem("Due soon", _DUE_STATE_DUE_SOON)
        self.due_state_combo.addItem("Blocked", _DUE_STATE_BLOCKED)
        self.due_state_combo.addItem("Not due", _DUE_STATE_NOT_DUE)
        self.due_state_combo.addItem("Inactive", _DUE_STATE_INACTIVE)
        self.status_combo.addItem("All statuses", None)
        for status in MaintenancePlanStatus:
            self.status_combo.addItem(status.value.title(), status.value)
        self.plan_type_combo.addItem("All plan types", None)
        for plan_type in MaintenancePlanType:
            self.plan_type_combo.addItem(plan_type.value.replace("_", " ").title(), plan_type.value)
        self.trigger_mode_combo.addItem("All trigger modes", None)
        for trigger_mode in MaintenanceTriggerMode:
            self.trigger_mode_combo.addItem(trigger_mode.value.title(), trigger_mode.value)

        filter_row.addWidget(QLabel("Site"), 0, 0)
        filter_row.addWidget(self.site_combo, 0, 1)
        filter_row.addWidget(QLabel("Due state"), 0, 2)
        filter_row.addWidget(self.due_state_combo, 0, 3)
        filter_row.addWidget(QLabel("Plan status"), 1, 0)
        filter_row.addWidget(self.status_combo, 1, 1)
        filter_row.addWidget(QLabel("Plan type"), 1, 2)
        filter_row.addWidget(self.plan_type_combo, 1, 3)
        filter_row.addWidget(QLabel("Trigger"), 2, 0)
        filter_row.addWidget(self.trigger_mode_combo, 2, 1)
        filter_row.addWidget(QLabel("Search"), 2, 2)
        filter_row.addWidget(self.search_edit, 2, 3)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Visible Plans", "-", "Current preventive library in scope", CFG.COLOR_ACCENT)
        self.due_now_card = KpiCard("Due Now", "-", "Plans ready to generate work", CFG.COLOR_WARNING)
        self.due_soon_card = KpiCard("Due Soon", "-", "Plans due within the next 30 days", CFG.COLOR_SUCCESS)
        self.blocked_card = KpiCard("Blocked", "-", "Hybrid or sensor issues needing planner review", CFG.COLOR_ACCENT)
        for card in (self.total_card, self.due_now_card, self.due_soon_card, self.blocked_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        content_row = QHBoxLayout()
        content_row.setSpacing(CFG.SPACING_MD)
        content_row.addWidget(self._build_plan_panel(), 3)
        content_row.addWidget(self._build_detail_panel(), 2)
        root.addLayout(content_row, 1)

        self.site_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self.reload_data)
        )
        self.due_state_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self.reload_plan_rows)
        )
        self.status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self.reload_plan_rows)
        )
        self.plan_type_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self.reload_plan_rows)
        )
        self.trigger_mode_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self.reload_plan_rows)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self.reload_plan_rows)
        )
        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self.reload_data)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.plan_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Preventive Plans", callback=self._on_plan_selection_changed)
        )

    def _build_plan_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenancePreventiveQueueSurface",
            alt=False,
        )
        title = QLabel("Preventive Queue")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Calendar, sensor, and hybrid preventive plans with live due-state interpretation.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.plan_table = build_admin_table(
            headers=("Plan", "Anchor", "Status", "Trigger", "Due State", "Next Due"),
            resize_modes=(
                self._stretch(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.plan_table)
        return panel

    def _build_detail_panel(self) -> QWidget:
        panel, layout = build_admin_surface_card(
            object_name="maintenancePreventiveDetailSurface",
            alt=False,
        )
        title = QLabel("Selected Preventive Plan")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Review generation target, trigger state, next due values, and task-library assignments.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.detail_title = QLabel("No preventive plan selected")
        self.detail_title.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        layout.addWidget(self.detail_title)
        self.detail_summary = QLabel("Select a preventive plan to inspect its trigger state and task library.")
        self.detail_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.detail_summary.setWordWrap(True)
        layout.addWidget(self.detail_summary)

        task_title = QLabel("Plan Tasks")
        task_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        layout.addWidget(task_title)
        self.task_table = build_admin_table(
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
        layout.addWidget(self.task_table)
        return panel

    def reload_data(self) -> None:
        selected_site_id = selected_combo_value(self.site_combo)
        try:
            sites = self._site_service.list_sites(active_only=None)
            assets = self._asset_service.list_assets(active_only=None, site_id=selected_site_id)
            systems = self._system_service.list_systems(active_only=None, site_id=selected_site_id)
            sensors = self._sensor_service.list_sensors(active_only=None, site_id=selected_site_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plans", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plans", f"Failed to load preventive filters: {exc}")
            return

        self._site_labels = {row.id: row.name for row in sites}
        self._asset_labels = {row.id: f"{row.asset_code} - {row.name}" for row in assets}
        self._system_labels = {row.id: f"{row.system_code} - {row.name}" for row in systems}
        self._sensor_labels = {row.id: f"{row.sensor_code} - {row.sensor_name}" for row in sensors}
        try:
            task_templates = self._task_template_service.list_task_templates(active_only=None)
        except BusinessRuleError:
            task_templates = []
        self._task_template_labels = {
            row.id: f"{row.task_template_code} - {row.name}"
            for row in task_templates
        }
        reset_combo_options(
            self.site_combo,
            placeholder="All sites",
            options=[(f"{row.site_code} - {row.name}", row.id) for row in sites],
            selected_value=selected_site_id,
        )
        self.reload_plan_rows()

    def reload_plan_rows(self) -> None:
        selected_plan_id = self._selected_plan_id()
        site_id = selected_combo_value(self.site_combo)
        status = selected_combo_value(self.status_combo)
        plan_type = selected_combo_value(self.plan_type_combo)
        trigger_mode = selected_combo_value(self.trigger_mode_combo)
        search_text = self.search_edit.text().strip()
        due_state_filter = selected_combo_value(self.due_state_combo) or _DUE_STATE_ALL
        try:
            plans = self._preventive_plan_service.search_preventive_plans(
                search_text=search_text,
                active_only=None,
                site_id=site_id,
                status=status,
                plan_type=plan_type,
                trigger_mode=trigger_mode,
            )
            candidate_rows = self._preventive_generation_service.list_due_candidates(site_id=site_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plans", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plans", f"Failed to load preventive plans: {exc}")
            return

        candidate_by_plan_id = {row.plan_id: row for row in candidate_rows}
        visible_rows = [
            self._build_plan_row(plan, candidate_by_plan_id.get(plan.id))
            for plan in plans
        ]
        if due_state_filter != _DUE_STATE_ALL:
            visible_rows = [row for row in visible_rows if row.due_state == due_state_filter]
        self._visible_rows = visible_rows

        self.total_card.set_value(str(len(visible_rows)))
        self.due_now_card.set_value(str(sum(1 for row in visible_rows if row.due_state == _DUE_STATE_DUE)))
        self.due_soon_card.set_value(str(sum(1 for row in visible_rows if row.is_due_soon)))
        self.blocked_card.set_value(str(sum(1 for row in visible_rows if row.due_state == _DUE_STATE_BLOCKED)))
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.due_badge.setText(f"{sum(1 for row in visible_rows if row.due_state == _DUE_STATE_DUE)} due now")
        self.blocked_badge.setText(
            f"{sum(1 for row in visible_rows if row.due_state == _DUE_STATE_BLOCKED)} blocked"
        )
        self.filter_summary.setText(
            "Filters: "
            f"{self.site_combo.currentText()} | {self.due_state_combo.currentText()} | "
            f"{self.status_combo.currentText()} | {self.plan_type_combo.currentText()} | {self.trigger_mode_combo.currentText()}"
            + (f" | Search: {search_text}" if search_text else "")
        )
        self._populate_plan_table(selected_plan_id=selected_plan_id)

    def _populate_plan_table(self, *, selected_plan_id: str | None) -> None:
        self.plan_table.blockSignals(True)
        self.plan_table.setRowCount(len(self._visible_rows))
        selected_row = 0 if self._visible_rows else -1
        for row_index, view in enumerate(self._visible_rows):
            plan = view.plan
            values = (
                f"{plan.plan_code} - {plan.name}",
                self._anchor_label(plan),
                plan.status.value.title(),
                plan.trigger_mode.value.title(),
                self._due_state_label(view),
                self._next_due_label(view),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, plan.id)
                self.plan_table.setItem(row_index, column, item)
            if selected_plan_id and plan.id == selected_plan_id:
                selected_row = row_index
        self.plan_table.blockSignals(False)
        if selected_row >= 0:
            self.plan_table.selectRow(selected_row)
            self._refresh_plan_details(self._visible_rows[selected_row])
            return
        self._clear_plan_details()

    def _refresh_plan_details(self, view: _PreventivePlanRow) -> None:
        plan = view.plan
        try:
            plan_tasks = sorted(
                self._preventive_plan_task_service.list_plan_tasks(plan_id=plan.id),
                key=lambda row: row.sequence_no,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Preventive Plans", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Preventive Plans", f"Failed to load preventive-plan detail: {exc}")
            return

        self.detail_title.setText(f"{plan.plan_code} - {plan.name}")
        self.detail_summary.setText(
            "\n".join(
                [
                    f"Anchor: {self._anchor_label(plan)}",
                    f"Type: {plan.plan_type.value.replace('_', ' ').title()} | Status: {plan.status.value.title()} | Priority: {plan.priority.value.title()}",
                    f"Trigger: {self._trigger_summary(plan)} | Target: {'Work Order' if plan.auto_generate_work_order else 'Work Request'}",
                    f"Due state: {self._due_state_label(view)} | Reason: {view.due_reason or '-'}",
                    f"Last generated: {format_timestamp(plan.last_generated_at)} | Last completed: {format_timestamp(plan.last_completed_at)}",
                    f"Next due at: {format_timestamp(plan.next_due_at)} | Next counter: {plan.next_due_counter if plan.next_due_counter is not None else '-'}",
                    f"Controls: {'Shutdown required' if plan.requires_shutdown else 'No shutdown'} | {'Approval required' if plan.approval_required else 'No approval'}",
                    f"Notes: {plan.notes or '-'}",
                ]
            )
        )
        self._populate_task_table(view, plan_tasks)

    def _populate_task_table(
        self,
        view: _PreventivePlanRow,
        plan_tasks: list[MaintenancePreventivePlanTask],
    ) -> None:
        self.task_table.setRowCount(len(plan_tasks))
        selected_ids = set(view.selected_plan_task_ids)
        blocked_ids = set(view.blocked_plan_task_ids)
        for row_index, plan_task in enumerate(plan_tasks):
            values = (
                str(plan_task.sequence_no),
                self._task_template_labels.get(plan_task.task_template_id, plan_task.task_template_id),
                "Inherit plan" if plan_task.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN else "Task override",
                self._plan_task_trigger_summary(plan_task),
                self._plan_task_due_state(plan_task, view, selected_ids=selected_ids, blocked_ids=blocked_ids),
                str(plan_task.estimated_minutes_override or "-"),
            )
            for column, value in enumerate(values):
                self.task_table.setItem(row_index, column, QTableWidgetItem(value))

    def _clear_plan_details(self) -> None:
        self.detail_title.setText("No preventive plan selected")
        self.detail_summary.setText("Select a preventive plan to inspect its trigger state and task library.")
        self.task_table.setRowCount(0)

    def _build_plan_row(self, plan: MaintenancePreventivePlan, candidate) -> _PreventivePlanRow:
        now = datetime.now(timezone.utc)
        next_due_at = self._ensure_utc_datetime(plan.next_due_at)
        if not plan.is_active or plan.status != MaintenancePlanStatus.ACTIVE:
            due_state = _DUE_STATE_INACTIVE
            due_reason = "Preventive plan is not active for due generation."
            generation_target = "WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST"
            selected_plan_task_ids: tuple[str, ...] = ()
            blocked_plan_task_ids: tuple[str, ...] = ()
        elif candidate is not None:
            due_state = candidate.due_state
            due_reason = candidate.due_reason
            generation_target = candidate.generation_target
            selected_plan_task_ids = candidate.selected_plan_task_ids
            blocked_plan_task_ids = candidate.blocked_plan_task_ids
        else:
            due_state = _DUE_STATE_NOT_DUE
            due_reason = "Preventive plan is active but has no current due candidate."
            generation_target = "WORK_ORDER" if plan.auto_generate_work_order else "WORK_REQUEST"
            selected_plan_task_ids = ()
            blocked_plan_task_ids = ()
        is_due_soon = (
            due_state == _DUE_STATE_NOT_DUE
            and next_due_at is not None
            and now <= next_due_at <= now + _DUE_SOON_WINDOW
        )
        return _PreventivePlanRow(
            plan=plan,
            due_state=due_state,
            due_reason=due_reason,
            generation_target=generation_target,
            selected_plan_task_ids=selected_plan_task_ids,
            blocked_plan_task_ids=blocked_plan_task_ids,
            is_due_soon=is_due_soon,
        )

    def _selected_plan_id(self) -> str | None:
        row = self.plan_table.currentRow()
        if row < 0:
            return None
        item = self.plan_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _anchor_label(self, plan: MaintenancePreventivePlan) -> str:
        if plan.asset_id:
            return self._asset_labels.get(plan.asset_id, plan.asset_id)
        if plan.system_id:
            return self._system_labels.get(plan.system_id, plan.system_id)
        if plan.component_id:
            return plan.component_id
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
        view: _PreventivePlanRow,
        *,
        selected_ids: set[str],
        blocked_ids: set[str],
    ) -> str:
        if view.due_state == _DUE_STATE_INACTIVE:
            return "Inactive"
        if plan_task.id in selected_ids:
            return "Due"
        if plan_task.id in blocked_ids:
            return "Blocked"
        if plan_task.trigger_scope == MaintenancePlanTaskTriggerScope.INHERIT_PLAN:
            return "Plan state"
        return "Idle"

    def _next_due_label(self, view: _PreventivePlanRow) -> str:
        if view.due_state == _DUE_STATE_BLOCKED:
            return "Review exception"
        if view.plan.next_due_at is not None:
            return format_timestamp(view.plan.next_due_at)
        if view.plan.next_due_counter is not None:
            return str(view.plan.next_due_counter)
        return "-"

    def _due_state_label(self, view: _PreventivePlanRow) -> str:
        if view.due_state == _DUE_STATE_DUE_SOON:
            return "Due Soon"
        if view.is_due_soon and view.due_state == _DUE_STATE_NOT_DUE:
            return "Due Soon"
        return view.due_state.replace("_", " ").title()

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
    def _ensure_utc_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

    def _on_plan_selection_changed(self) -> None:
        plan_id = self._selected_plan_id()
        if not plan_id:
            self._clear_plan_details()
            return
        for view in self._visible_rows:
            if view.plan.id == plan_id:
                self._refresh_plan_details(view)
                return
        self._clear_plan_details()

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


__all__ = ["MaintenancePreventivePlansTab"]
