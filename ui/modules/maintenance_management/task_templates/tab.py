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
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
)
from core.modules.maintenance_management.domain import MaintenanceTemplateStatus
from src.core.platform.auth import UserSessionContext
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from ui.modules.maintenance_management.shared import (
    build_maintenance_header,
    make_accent_badge,
    make_filter_toggle_button,
    make_meta_badge,
    reset_combo_options,
    selected_combo_value,
    set_filter_panel_visible,
)
from ui.modules.maintenance_management.task_templates.detail_dialog import MaintenanceTaskTemplateDetailDialog
from ui.modules.maintenance_management.task_templates.edit_dialogs import MaintenanceTaskTemplateEditDialog
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.modules.project_management.dashboard.widgets import KpiCard
from src.ui.platform.widgets.admin_surface import build_admin_surface_card, build_admin_table
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class MaintenanceTaskTemplatesTab(QWidget):
    def __init__(
        self,
        *,
        task_template_service: MaintenanceTaskTemplateService,
        task_step_template_service: MaintenanceTaskStepTemplateService,
        platform_runtime_application_service: PlatformRuntimeApplicationService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._task_template_service = task_template_service
        self._task_step_template_service = task_step_template_service
        self._platform_runtime_application_service = platform_runtime_application_service
        self._user_session = user_session
        self._can_manage = has_permission(user_session, "maintenance.manage")
        self._rows = []
        self._all_rows = []
        self._all_steps = []
        self._detail_dialog: MaintenanceTaskTemplateDetailDialog | None = None
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
        self.count_badge = make_meta_badge("0 templates")
        self.active_badge = make_meta_badge("0 active")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenanceTaskTemplatesHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Task Templates",
            subtitle_text="Author reusable maintenance task templates and keep step-template authoring inside the focused detail popup.",
            badges=(self.context_badge, self.count_badge, self.active_badge, self.access_badge),
        )

        actions, actions_layout = build_admin_surface_card(
            object_name="maintenanceTaskTemplatesActionSurface",
            alt=False,
        )
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_template = QPushButton("New Template")
        self.btn_edit_template = QPushButton("Edit Template")
        self.btn_toggle_active = QPushButton("Toggle Active")
        self.btn_open_detail = QPushButton("Open Detail")
        for button, variant in (
            (self.btn_new_template, "primary"),
            (self.btn_edit_template, "secondary"),
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
            object_name="maintenanceTaskTemplatesControlSurface",
            alt=True,
        )
        toolbar_row = QHBoxLayout()
        toolbar_row.setSpacing(CFG.SPACING_SM)
        self.filter_summary = QLabel("Filters: Active only | All types | All statuses")
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
        filter_layout = QHBoxLayout(self.filter_panel)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(CFG.SPACING_MD)
        self.active_combo = QComboBox()
        self.active_combo.addItem("Active only", True)
        self.active_combo.addItem("Inactive only", False)
        self.active_combo.addItem("All statuses", None)
        self.maintenance_type_combo = QComboBox()
        self.template_status_combo = QComboBox()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by code, name, type, status, skill, or notes")
        filter_layout.addWidget(QLabel("Lifecycle"))
        filter_layout.addWidget(self.active_combo)
        filter_layout.addWidget(QLabel("Type"))
        filter_layout.addWidget(self.maintenance_type_combo)
        filter_layout.addWidget(QLabel("Template Status"))
        filter_layout.addWidget(self.template_status_combo)
        filter_layout.addWidget(QLabel("Search"))
        filter_layout.addWidget(self.search_edit, 1)
        controls_layout.addWidget(self.filter_panel)
        set_filter_panel_visible(button=self.btn_filters, panel=self.filter_panel, visible=False)
        root.addWidget(controls)

        summary_row = QHBoxLayout()
        summary_row.setSpacing(CFG.SPACING_MD)
        self.total_card = KpiCard("Templates", "-", "Visible in current library filter", CFG.COLOR_ACCENT)
        self.active_card = KpiCard("Active", "-", "Ready for planning and generation", CFG.COLOR_SUCCESS)
        self.step_card = KpiCard("Step Templates", "-", "Reusable steps across the library", CFG.COLOR_WARNING)
        for card in (self.total_card, self.active_card, self.step_card):
            summary_row.addWidget(card, 1)
        root.addLayout(summary_row)

        panel, layout = build_admin_surface_card(
            object_name="maintenanceTaskTemplatesGridSurface",
            alt=False,
        )
        title = QLabel("Task Template Library")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel(
            "Use this queue for template selection, then open the detail popup to manage reusable step templates."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.selection_summary = QLabel(
            "Select a task template, then click Open Detail to inspect metadata and step templates."
        )
        self.selection_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_summary.setWordWrap(True)
        layout.addWidget(self.selection_summary)
        self.table = build_admin_table(
            headers=("Code", "Name", "Type", "Revision", "Status", "Skill", "Minutes", "Active"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.table)
        root.addWidget(panel, 1)

        self.active_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Task Templates", callback=self.reload_rows)
        )
        self.maintenance_type_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Task Templates", callback=self.reload_rows)
        )
        self.template_status_combo.currentIndexChanged.connect(
            make_guarded_slot(self, title="Task Templates", callback=self.reload_rows)
        )
        self.search_edit.returnPressed.connect(
            make_guarded_slot(self, title="Task Templates", callback=self.reload_rows)
        )
        self.btn_filters.clicked.connect(self._toggle_filters)
        self.btn_refresh.clicked.connect(make_guarded_slot(self, title="Task Templates", callback=self.reload_data))
        self.btn_new_template.clicked.connect(
            make_guarded_slot(self, title="Task Templates", callback=self.create_template)
        )
        self.btn_edit_template.clicked.connect(
            make_guarded_slot(self, title="Task Templates", callback=self.edit_template)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Task Templates", callback=self.toggle_active)
        )
        self.btn_open_detail.clicked.connect(
            make_guarded_slot(self, title="Task Templates", callback=self._open_detail_dialog)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        for button in (self.btn_new_template, self.btn_edit_template, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage, missing_permission="maintenance.manage")
        self._sync_actions()

    def reload_data(self) -> None:
        selected_type = selected_combo_value(self.maintenance_type_combo)
        selected_status = selected_combo_value(self.template_status_combo)
        try:
            all_rows = self._task_template_service.list_task_templates(active_only=None)
            all_steps = self._task_step_template_service.list_step_templates(active_only=None)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Task Templates", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Task Templates", f"Failed to load task templates: {exc}")
            return

        self._all_rows = all_rows
        self._all_steps = all_steps
        reset_combo_options(
            self.maintenance_type_combo,
            placeholder="All types",
            options=[(value, value) for value in self._maintenance_type_values(all_rows)],
            selected_value=selected_type,
        )
        reset_combo_options(
            self.template_status_combo,
            placeholder="All statuses",
            options=[(value.value.title(), value.value) for value in MaintenanceTemplateStatus],
            selected_value=selected_status,
        )
        self.reload_rows()

    def reload_rows(self) -> None:
        selected_template_id = self._selected_template_id()
        try:
            rows = self._task_template_service.search_task_templates(
                search_text=self.search_edit.text(),
                active_only=self.active_combo.currentData(),
                maintenance_type=selected_combo_value(self.maintenance_type_combo),
                template_status=selected_combo_value(self.template_status_combo),
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Task Templates", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Task Templates", f"Failed to refresh task templates: {exc}")
            return

        self._rows = rows
        self.context_badge.setText(f"Context: {self._context_label()}")
        self.count_badge.setText(f"{len(rows)} templates")
        self.active_badge.setText(f"{sum(1 for row in rows if row.is_active)} active")
        self.filter_summary.setText(
            "Filters: "
            f"{self.active_combo.currentText()} | {self.maintenance_type_combo.currentText()} | {self.template_status_combo.currentText()}"
            + (f" | Search: {self.search_edit.text().strip()}" if self.search_edit.text().strip() else "")
        )
        self.total_card.set_value(str(len(rows)))
        self.active_card.set_value(str(sum(1 for row in rows if row.is_active)))
        self.step_card.set_value(str(len(self._all_steps)))
        self._populate_table(selected_template_id=selected_template_id)

    def create_template(self) -> None:
        dialog = MaintenanceTaskTemplateEditDialog(parent=self)
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                self._task_template_service.create_task_template(
                    task_template_code=dialog.task_template_code,
                    name=dialog.name,
                    description=dialog.description,
                    maintenance_type=dialog.maintenance_type,
                    revision_no=dialog.revision_no,
                    template_status=dialog.template_status,
                    estimated_minutes=dialog.estimated_minutes,
                    required_skill=dialog.required_skill,
                    requires_shutdown=dialog.requires_shutdown,
                    requires_permit=dialog.requires_permit,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Task Templates", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Task Templates", f"Failed to create task template: {exc}")
                return
            break
        self.reload_data()

    def edit_template(self) -> None:
        task_template = self._selected_template()
        if task_template is None:
            QMessageBox.information(self, "Task Templates", "Select a task template to edit.")
            return
        dialog = MaintenanceTaskTemplateEditDialog(task_template=task_template, parent=self)
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                self._task_template_service.update_task_template(
                    task_template.id,
                    task_template_code=dialog.task_template_code,
                    name=dialog.name,
                    description=dialog.description,
                    maintenance_type=dialog.maintenance_type,
                    revision_no=dialog.revision_no,
                    template_status=dialog.template_status,
                    estimated_minutes=dialog.estimated_minutes,
                    required_skill=dialog.required_skill,
                    requires_shutdown=dialog.requires_shutdown,
                    requires_permit=dialog.requires_permit,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                    expected_version=task_template.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Task Templates", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Task Templates", str(exc))
                self.reload_data()
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Task Templates", f"Failed to update task template: {exc}")
                return
            break
        self.reload_data()

    def toggle_active(self) -> None:
        task_template = self._selected_template()
        if task_template is None:
            QMessageBox.information(self, "Task Templates", "Select a task template to update.")
            return
        try:
            self._task_template_service.update_task_template(
                task_template.id,
                is_active=not task_template.is_active,
                expected_version=task_template.version,
            )
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Task Templates", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Task Templates", f"Failed to update task template: {exc}")
            return
        self.reload_data()

    def _populate_table(self, *, selected_template_id: str | None) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(len(self._rows))
        selected_row = -1
        for row_index, row in enumerate(self._rows):
            values = (
                row.task_template_code,
                row.name,
                row.maintenance_type or "-",
                str(row.revision_no),
                row.template_status.value.title(),
                row.required_skill or "-",
                str(row.estimated_minutes) if row.estimated_minutes is not None else "-",
                "Yes" if row.is_active else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.table.setItem(row_index, column, item)
            if selected_template_id and row.id == selected_template_id:
                selected_row = row_index
        self.table.blockSignals(False)
        if selected_row >= 0:
            self.table.selectRow(selected_row)
        else:
            self.table.clearSelection()
        self._sync_actions()

    def _selected_template_id(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _selected_template(self):
        template_id = self._selected_template_id()
        if not template_id:
            return None
        try:
            return self._task_template_service.get_task_template(template_id)
        except Exception:  # noqa: BLE001
            return None

    def _open_detail_dialog(self) -> None:
        template_id = self._selected_template_id()
        if not template_id:
            QMessageBox.information(self, "Task Templates", "Select a task template to open its detail view.")
            return
        dialog = MaintenanceTaskTemplateDetailDialog(
            task_template_service=self._task_template_service,
            task_step_template_service=self._task_step_template_service,
            can_manage=self._can_manage,
            parent=self,
        )
        dialog.load_task_template(template_id)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        self._detail_dialog = dialog

    def _sync_actions(self) -> None:
        task_template = self._selected_template()
        if task_template is None:
            self.selection_summary.setText(
                "Select a task template, then click Open Detail to inspect metadata and step templates."
            )
            self.btn_new_template.setEnabled(self._can_manage)
            self.btn_edit_template.setEnabled(False)
            self.btn_toggle_active.setEnabled(False)
            self.btn_open_detail.setEnabled(False)
            return
        step_count = sum(1 for row in self._all_steps if row.task_template_id == task_template.id)
        self.selection_summary.setText(
            f"Selected: {task_template.task_template_code} | Status: {task_template.template_status.value.title()} | Steps: {step_count}"
        )
        self.btn_new_template.setEnabled(self._can_manage)
        self.btn_edit_template.setEnabled(self._can_manage)
        self.btn_toggle_active.setEnabled(self._can_manage)
        self.btn_open_detail.setEnabled(True)

    def _toggle_filters(self) -> None:
        set_filter_panel_visible(
            button=self.btn_filters,
            panel=self.filter_panel,
            visible=not self.filter_panel.isVisible(),
        )

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
    def _maintenance_type_values(rows) -> list[str]:
        values = {str(row.maintenance_type).strip().upper() for row in rows if str(row.maintenance_type).strip()}
        return sorted(values)

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceTaskTemplatesTab"]
