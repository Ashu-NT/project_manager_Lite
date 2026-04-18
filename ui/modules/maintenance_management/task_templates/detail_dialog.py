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
    MaintenanceTaskStepTemplateService,
    MaintenanceTaskTemplateService,
)
from core.modules.maintenance_management.domain import MaintenanceTaskStepTemplate
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, NotFoundError, ValidationError
from src.core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from ui.modules.maintenance_management.shared import (
    MaintenanceWorkbenchNavigator,
    MaintenanceWorkbenchSection,
    build_maintenance_header,
    format_timestamp,
    make_accent_badge,
    make_meta_badge,
)
from ui.modules.maintenance_management.task_templates.edit_dialogs import MaintenanceTaskStepTemplateEditDialog
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import apply_permission_hint, make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class MaintenanceTaskTemplateDetailDialog(QDialog):
    def __init__(
        self,
        *,
        task_template_service: MaintenanceTaskTemplateService,
        task_step_template_service: MaintenanceTaskStepTemplateService,
        can_manage: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._task_template_service = task_template_service
        self._task_step_template_service = task_step_template_service
        self._can_manage = can_manage
        self._current_task_template_id: str | None = None
        self._step_rows: list[MaintenanceTaskStepTemplate] = []

        self.setWindowTitle("Task Template Detail")
        self.resize(1120, 760)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.context_badge = make_accent_badge("Template")
        self.step_count_badge = make_meta_badge("0 steps")
        self.active_badge = make_meta_badge("Inactive")
        self.access_badge = make_meta_badge("Manage Enabled" if self._can_manage else "Read Only")
        build_maintenance_header(
            root=root,
            object_name="maintenanceTaskTemplateDetailHeaderCard",
            eyebrow_text="MAINTENANCE LIBRARIES",
            title_text="Task Template Detail",
            subtitle_text="Inspect template metadata, revision state, and reusable step definitions without crowding the main library queue.",
            badges=(self.context_badge, self.step_count_badge, self.active_badge, self.access_badge),
        )

        self.workbench = MaintenanceWorkbenchNavigator(
            object_name="maintenanceTaskTemplateDetailWorkbench",
            parent=self,
        )
        self.overview_widget = self._build_overview_widget()
        self.step_widget = self._build_step_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(key="overview", label="Overview", widget=self.overview_widget),
                MaintenanceWorkbenchSection(
                    key="step_templates",
                    label="Step Templates",
                    widget=self.step_widget,
                ),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

        self.step_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Task Template Detail", callback=self._sync_step_actions)
        )
        self.btn_new_step.clicked.connect(
            make_guarded_slot(self, title="Task Template Detail", callback=self._create_step)
        )
        self.btn_edit_step.clicked.connect(
            make_guarded_slot(self, title="Task Template Detail", callback=self._edit_step)
        )
        self.btn_toggle_step.clicked.connect(
            make_guarded_slot(self, title="Task Template Detail", callback=self._toggle_step_active)
        )
        apply_permission_hint(self.btn_new_step, allowed=self._can_manage, missing_permission="maintenance.manage")
        apply_permission_hint(self.btn_edit_step, allowed=self._can_manage, missing_permission="maintenance.manage")
        apply_permission_hint(self.btn_toggle_step, allowed=self._can_manage, missing_permission="maintenance.manage")
        domain_events.domain_changed.connect(self._on_domain_change)
        self._sync_step_actions()

    def _build_overview_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceTaskTemplateDetailOverviewSurface",
            alt=False,
        )
        title = QLabel("Template Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel(
            "Revision, shutdown, permit, skill, and planning notes stay here while reusable step authoring stays in its own section."
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
            ("Type", "maintenance_type"),
            ("Status", "template_status"),
            ("Revision", "revision_no"),
            ("Estimated Minutes", "estimated_minutes"),
            ("Required Skill", "required_skill"),
            ("Flags", "flags"),
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

    def _build_step_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceTaskTemplateDetailStepSurface",
            alt=False,
        )
        title = QLabel("Step Templates")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel(
            "Manage the reusable execution steps that will be copied into preventive and work-order execution records."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.step_summary = QLabel("Select a step template to edit or toggle it.")
        self.step_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.step_summary.setWordWrap(True)
        layout.addWidget(self.step_summary)
        self.step_table = build_admin_table(
            headers=("Step", "Instruction", "Hint", "Requirements", "Active"),
            resize_modes=(
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
                self._stretch(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.step_table)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        self.btn_new_step = QPushButton("New Step")
        self.btn_edit_step = QPushButton("Edit Step")
        self.btn_toggle_step = QPushButton("Toggle Active")
        for button in (self.btn_new_step, self.btn_edit_step, self.btn_toggle_step):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
            action_row.addWidget(button)
        action_row.addStretch(1)
        layout.addLayout(action_row)
        return widget

    def load_task_template(self, task_template_id: str, *, selected_step_id: str | None = None) -> None:
        self._current_task_template_id = task_template_id
        try:
            task_template = self._task_template_service.get_task_template(task_template_id)
            step_rows = self._task_step_template_service.list_step_templates(
                task_template_id=task_template_id,
                active_only=None,
            )
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Task Template Detail", str(exc))
            return
        except NotFoundError as exc:
            QMessageBox.warning(self, "Task Template Detail", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Task Template Detail", f"Failed to load task template detail: {exc}")
            return

        self.context_badge.setText(f"Template: {task_template.task_template_code}")
        self.step_count_badge.setText(f"{len(step_rows)} steps")
        self.active_badge.setText("Active" if task_template.is_active else "Inactive")
        self.setWindowTitle(f"Task Template Detail - {task_template.task_template_code}")
        self._step_rows = sorted(step_rows, key=lambda row: (row.sort_order, row.step_number))
        self._populate_overview(task_template)
        self._populate_step_table(selected_step_id=selected_step_id)
        self.workbench.set_current_section("overview")

    def _populate_overview(self, task_template) -> None:
        self.overview_labels["code"].setText(task_template.task_template_code)
        self.overview_labels["name"].setText(task_template.name)
        self.overview_labels["maintenance_type"].setText(task_template.maintenance_type or "-")
        self.overview_labels["template_status"].setText(task_template.template_status.value.title())
        self.overview_labels["revision_no"].setText(str(task_template.revision_no))
        self.overview_labels["estimated_minutes"].setText(
            str(task_template.estimated_minutes) if task_template.estimated_minutes is not None else "-"
        )
        self.overview_labels["required_skill"].setText(task_template.required_skill or "-")
        flags: list[str] = []
        if task_template.requires_shutdown:
            flags.append("Shutdown")
        if task_template.requires_permit:
            flags.append("Permit")
        if task_template.is_active:
            flags.append("Active")
        self.overview_labels["flags"].setText(", ".join(flags) if flags else "-")
        self.overview_labels["created_at"].setText(format_timestamp(task_template.created_at))
        self.overview_labels["updated_at"].setText(format_timestamp(task_template.updated_at))
        self.description_label.setText(task_template.description or "-")
        self.notes_label.setText(task_template.notes or "-")

    def _populate_step_table(self, *, selected_step_id: str | None) -> None:
        self.step_table.blockSignals(True)
        self.step_table.setRowCount(len(self._step_rows))
        selected_row = -1
        for row_index, row in enumerate(self._step_rows):
            values = (
                str(row.step_number),
                row.instruction,
                row.hint_level or "-",
                self._format_step_requirements(row),
                "Yes" if row.is_active else "No",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, row.id)
                self.step_table.setItem(row_index, column, item)
            if selected_step_id and row.id == selected_step_id:
                selected_row = row_index
        self.step_table.blockSignals(False)
        if selected_row >= 0:
            self.step_table.selectRow(selected_row)
        else:
            self.step_table.clearSelection()
        self._sync_step_actions()

    def _create_step(self) -> None:
        if not self._current_task_template_id:
            return
        dialog = MaintenanceTaskStepTemplateEditDialog(parent=self)
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                row = self._task_step_template_service.create_step_template(
                    task_template_id=self._current_task_template_id,
                    step_number=dialog.step_number,
                    instruction=dialog.instruction,
                    expected_result=dialog.expected_result,
                    hint_level=dialog.hint_level,
                    hint_text=dialog.hint_text,
                    requires_confirmation=dialog.requires_confirmation,
                    requires_measurement=dialog.requires_measurement,
                    requires_photo=dialog.requires_photo,
                    measurement_unit=dialog.measurement_unit,
                    sort_order=dialog.sort_order,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Task Template Detail", str(exc))
                continue
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Task Template Detail", f"Failed to create step template: {exc}")
                return
            self.load_task_template(self._current_task_template_id, selected_step_id=row.id)
            self.workbench.set_current_section("step_templates")
            return

    def _edit_step(self) -> None:
        step = self._selected_step()
        if step is None:
            QMessageBox.information(self, "Task Template Detail", "Select a step template to edit.")
            return
        dialog = MaintenanceTaskStepTemplateEditDialog(step_template=step, parent=self)
        while True:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            try:
                row = self._task_step_template_service.update_step_template(
                    step.id,
                    step_number=dialog.step_number,
                    instruction=dialog.instruction,
                    expected_result=dialog.expected_result,
                    hint_level=dialog.hint_level,
                    hint_text=dialog.hint_text,
                    requires_confirmation=dialog.requires_confirmation,
                    requires_measurement=dialog.requires_measurement,
                    requires_photo=dialog.requires_photo,
                    measurement_unit=dialog.measurement_unit,
                    sort_order=dialog.sort_order,
                    is_active=dialog.is_active,
                    notes=dialog.notes,
                    expected_version=step.version,
                )
            except (ValidationError, BusinessRuleError, NotFoundError) as exc:
                QMessageBox.warning(self, "Task Template Detail", str(exc))
                continue
            except ConcurrencyError as exc:
                QMessageBox.warning(self, "Task Template Detail", str(exc))
                self.load_task_template(self._current_task_template_id or "", selected_step_id=step.id)
                return
            except Exception as exc:  # noqa: BLE001
                QMessageBox.critical(self, "Task Template Detail", f"Failed to update step template: {exc}")
                return
            self.load_task_template(self._current_task_template_id or "", selected_step_id=row.id)
            self.workbench.set_current_section("step_templates")
            return

    def _toggle_step_active(self) -> None:
        step = self._selected_step()
        if step is None:
            QMessageBox.information(self, "Task Template Detail", "Select a step template to update.")
            return
        try:
            row = self._task_step_template_service.update_step_template(
                step.id,
                is_active=not step.is_active,
                expected_version=step.version,
            )
        except (ValidationError, BusinessRuleError, NotFoundError, ConcurrencyError) as exc:
            QMessageBox.warning(self, "Task Template Detail", str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Task Template Detail", f"Failed to update step template: {exc}")
            return
        self.load_task_template(self._current_task_template_id or "", selected_step_id=row.id)
        self.workbench.set_current_section("step_templates")

    def _selected_step(self) -> MaintenanceTaskStepTemplate | None:
        step_id = self._selected_step_id()
        if not step_id:
            return None
        return next((row for row in self._step_rows if row.id == step_id), None)

    def _selected_step_id(self) -> str | None:
        row = self.step_table.currentRow()
        if row < 0:
            return None
        item = self.step_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return str(value) if value else None

    def _sync_step_actions(self) -> None:
        step = self._selected_step()
        if step is None:
            self.step_summary.setText("Select a step template to edit or toggle it.")
            self.btn_new_step.setEnabled(self._can_manage)
            self.btn_edit_step.setEnabled(False)
            self.btn_toggle_step.setEnabled(False)
            return
        self.step_summary.setText(
            f"Selected: step {step.step_number} | Requirements: {self._format_step_requirements(step)} | Active: {'Yes' if step.is_active else 'No'}"
        )
        self.btn_new_step.setEnabled(self._can_manage)
        self.btn_edit_step.setEnabled(self._can_manage)
        self.btn_toggle_step.setEnabled(self._can_manage)

    def _on_domain_change(self, event: DomainChangeEvent) -> None:
        if getattr(event, "scope_code", "") != "maintenance_management":
            return
        if self._current_task_template_id is None:
            return
        if event.entity_type not in {"maintenance_task_template", "maintenance_task_step_template"}:
            return
        self.load_task_template(self._current_task_template_id, selected_step_id=self._selected_step_id())

    @staticmethod
    def _format_step_requirements(step: MaintenanceTaskStepTemplate) -> str:
        flags: list[str] = []
        if step.requires_confirmation:
            flags.append("Confirm")
        if step.requires_measurement:
            unit = f" {step.measurement_unit}" if step.measurement_unit else ""
            flags.append(f"Measure{unit}")
        if step.requires_photo:
            flags.append("Photo")
        return ", ".join(flags) if flags else "Standard"

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceTaskTemplateDetailDialog"]
