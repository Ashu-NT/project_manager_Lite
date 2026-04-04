from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.modules.maintenance_management import (
    MaintenanceDocumentService,
    MaintenanceLaborService,
    MaintenanceWorkOrderMaterialRequirementService,
    MaintenanceWorkOrderService,
    MaintenanceWorkOrderTaskService,
    MaintenanceWorkOrderTaskStepService,
    MaintenanceWorkRequestService,
)
from core.modules.maintenance_management.domain import (
    MaintenanceTaskCompletionRule,
    MaintenanceWorkOrderTaskStatus,
    MaintenanceWorkOrderTaskStepStatus,
)
from core.platform.time.domain import TimeEntry
from ui.modules.maintenance_management.shared import (
    MaintenanceWorkbenchNavigator,
    MaintenanceWorkbenchSection,
    format_timestamp,
)
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.platform.admin.documents.viewer_dialogs import DocumentPreviewDialog
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import make_guarded_slot
from ui.platform.shared.styles.ui_config import UIConfig as CFG


_TASK_ID_ROLE = Qt.UserRole
_STEP_ID_ROLE = Qt.UserRole + 1


class MaintenanceWorkOrderDetailDialog(QDialog):
    def __init__(
        self,
        *,
        work_order_service: MaintenanceWorkOrderService,
        work_order_task_service: MaintenanceWorkOrderTaskService,
        work_order_task_step_service: MaintenanceWorkOrderTaskStepService,
        material_requirement_service: MaintenanceWorkOrderMaterialRequirementService,
        labor_service: MaintenanceLaborService | None = None,
        document_service: MaintenanceDocumentService | None = None,
        work_request_service: MaintenanceWorkRequestService | None = None,
        site_labels: dict[str, str],
        asset_labels: dict[str, str],
        location_labels: dict[str, str],
        system_labels: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._work_order_service = work_order_service
        self._work_order_task_service = work_order_task_service
        self._work_order_task_step_service = work_order_task_step_service
        self._material_requirement_service = material_requirement_service
        self._labor_service = labor_service
        self._document_service = document_service
        self._work_request_service = work_request_service
        self._site_labels = site_labels
        self._asset_labels = asset_labels
        self._location_labels = location_labels
        self._system_labels = system_labels
        self._current_work_order_id: str | None = None
        self._detail_tasks_by_id: dict[str, object] = {}
        self._detail_steps_by_id: dict[str, object] = {}
        self._step_ids_by_task_id: dict[str, list[str]] = {}
        self._detail_labor_entries_by_task_id: dict[str, list[TimeEntry]] = {}
        self._detail_documents_by_id: dict[str, object] = {}

        self.setWindowTitle("Work Order Detail")
        self.resize(1120, 760)
        self.setModal(False)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        root.setSpacing(CFG.SPACING_MD)

        self.title_label = QLabel("No work order selected")
        self.title_label.setStyleSheet(CFG.DASHBOARD_PROJECT_TITLE_STYLE)
        root.addWidget(self.title_label)

        self.workbench = MaintenanceWorkbenchNavigator(object_name="maintenanceWorkOrderDetailWorkbench", parent=self)
        self.overview_widget, self.overview_summary = self._build_overview_widget()
        self.tasks_widget = self._build_tasks_widget()
        self.steps_widget = self._build_steps_widget()
        self.labor_widget = self._build_labor_widget()
        self.materials_widget = self._build_materials_widget()
        self.evidence_widget = self._build_evidence_widget()
        self.workbench.set_sections(
            [
                MaintenanceWorkbenchSection(
                    key="overview",
                    label="Overview",
                    widget=self.overview_widget,
                ),
                MaintenanceWorkbenchSection(
                    key="tasks",
                    label="Tasks",
                    widget=self.tasks_widget,
                ),
                MaintenanceWorkbenchSection(
                    key="steps",
                    label="Task Steps",
                    widget=self.steps_widget,
                ),
                MaintenanceWorkbenchSection(
                    key="labor",
                    label="Labor",
                    widget=self.labor_widget,
                ),
                MaintenanceWorkbenchSection(
                    key="materials",
                    label="Materials",
                    widget=self.materials_widget,
                ),
                MaintenanceWorkbenchSection(
                    key="evidence",
                    label="Evidence",
                    widget=self.evidence_widget,
                ),
            ],
            initial_key="overview",
        )
        root.addWidget(self.workbench, 1)

        self.task_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._on_task_selection_changed)
        )
        self.step_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._on_step_selection_changed)
        )
        self.evidence_table.itemSelectionChanged.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._sync_evidence_actions)
        )
        self.btn_complete_task.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._on_complete_task)
        )
        self.btn_start_step.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._on_start_step)
        )
        self.btn_done_step.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._on_done_step)
        )
        self.btn_confirm_step.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._on_confirm_step)
        )
        self.btn_add_labor.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._on_add_labor_entry)
        )
        self.btn_preview_evidence.clicked.connect(
            make_guarded_slot(self, title="Maintenance Work Order Detail", callback=self._show_evidence_preview)
        )
        self._sync_task_actions()
        self._sync_step_actions()
        self._sync_labor_actions()
        self._sync_evidence_actions()

    def _build_overview_widget(self) -> tuple[QWidget, QLabel]:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrderDialogOverviewSurface",
            alt=False,
        )
        title = QLabel("Overview")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        summary = QLabel("Select a work order from the main queue to inspect execution context.")
        summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)
        return widget, summary

    def _build_tasks_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrderDialogTasksSurface",
            alt=False,
        )
        title = QLabel("Tasks")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Select a task to drive step execution and task completion for this work order.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.task_summary = QLabel("No task selected.")
        self.task_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.task_summary.setWordWrap(True)
        layout.addWidget(self.task_summary)
        self.task_table = build_admin_table(
            headers=("Task", "Assigned", "Status", "Skill", "Minutes", "Steps"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.task_table)
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.btn_complete_task = QPushButton("Complete Selected Task")
        self.btn_complete_task.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_complete_task.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_complete_task)
        layout.addLayout(action_row)
        return widget

    def _build_steps_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrderDialogStepsSurface",
            alt=False,
        )
        title = QLabel("Task Steps")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Execute and confirm the steps for the currently selected task.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.step_summary = QLabel("Select a task to review its steps.")
        self.step_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.step_summary.setWordWrap(True)
        layout.addWidget(self.step_summary)
        self.step_table = build_admin_table(
            headers=("Step", "Status", "Requirements", "Completion"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._stretch(),
                self._stretch(),
            ),
        )
        layout.addWidget(self.step_table)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        action_row.addWidget(QLabel("Measurement"))
        self.step_measurement_edit = QLineEdit()
        self.step_measurement_edit.setPlaceholderText("Enter measurement if the selected step requires one")
        action_row.addWidget(self.step_measurement_edit, 1)
        self.btn_start_step = QPushButton("Start Step")
        self.btn_done_step = QPushButton("Done Step")
        self.btn_confirm_step = QPushButton("Confirm Step")
        for button in (self.btn_start_step, self.btn_done_step, self.btn_confirm_step):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setStyleSheet(dashboard_action_button_style("secondary"))
            action_row.addWidget(button)
        layout.addLayout(action_row)
        return widget

    def _build_labor_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrderDialogLaborSurface",
            alt=False,
        )
        title = QLabel("Labor")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Book technician labor against the selected task through the shared time-entry boundary.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.labor_summary = QLabel("Select a task to review or book labor.")
        self.labor_summary.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.labor_summary.setWordWrap(True)
        layout.addWidget(self.labor_summary)
        self.labor_table = build_admin_table(
            headers=("Date", "Hours", "Author", "Note"),
            resize_modes=(
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._stretch(),
            ),
        )
        layout.addWidget(self.labor_table)
        action_row = QHBoxLayout()
        action_row.setSpacing(CFG.SPACING_SM)
        action_row.addWidget(QLabel("Date"))
        self.labor_date_edit = QDateEdit()
        self.labor_date_edit.setCalendarPopup(True)
        self.labor_date_edit.setDate(QDate.currentDate())
        self.labor_date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        action_row.addWidget(self.labor_date_edit)
        action_row.addWidget(QLabel("Hours"))
        self.labor_hours_spin = QDoubleSpinBox()
        self.labor_hours_spin.setDecimals(2)
        self.labor_hours_spin.setRange(0.25, 24.0)
        self.labor_hours_spin.setSingleStep(0.25)
        self.labor_hours_spin.setValue(1.0)
        self.labor_hours_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        action_row.addWidget(self.labor_hours_spin)
        action_row.addWidget(QLabel("Note"))
        self.labor_note_edit = QLineEdit()
        self.labor_note_edit.setPlaceholderText("Describe the work completed")
        action_row.addWidget(self.labor_note_edit, 1)
        self.btn_add_labor = QPushButton("Add Labor Entry")
        self.btn_add_labor.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_add_labor.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_add_labor)
        layout.addLayout(action_row)
        return widget

    def _build_materials_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrderDialogMaterialsSurface",
            alt=False,
        )
        title = QLabel("Materials")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Material requirements and issue readiness for this work order.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.material_table = build_admin_table(
            headers=("Material", "Required", "Issued", "Status", "Source"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.material_table)
        return widget

    def _build_evidence_widget(self) -> QWidget:
        widget, layout = build_admin_surface_card(
            object_name="maintenanceWorkOrderDialogEvidenceSurface",
            alt=False,
        )
        title = QLabel("Evidence")
        title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        subtitle = QLabel("Procedures, drawings, permits, and execution evidence linked to this work order.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        self.evidence_table = build_admin_table(
            headers=("Document", "Type", "Structure", "Uploaded"),
            resize_modes=(
                self._stretch(),
                self._resize_to_contents(),
                self._resize_to_contents(),
                self._resize_to_contents(),
            ),
        )
        layout.addWidget(self.evidence_table)
        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self.btn_preview_evidence = QPushButton("Preview Evidence")
        self.btn_preview_evidence.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_preview_evidence.setStyleSheet(dashboard_action_button_style("secondary"))
        action_row.addWidget(self.btn_preview_evidence)
        layout.addLayout(action_row)
        return widget

    def load_work_order(
        self,
        work_order_id: str,
        *,
        selected_task_id: str | None = None,
        selected_step_id: str | None = None,
    ) -> None:
        self._current_work_order_id = work_order_id
        work_order = self._work_order_service.get_work_order(work_order_id)
        tasks = sorted(
            self._work_order_task_service.list_tasks(work_order_id=work_order.id),
            key=lambda row: row.sequence_no,
        )
        step_rows_by_task_id = {
            task.id: sorted(
                self._work_order_task_step_service.list_steps(work_order_task_id=task.id),
                key=lambda row: row.step_number,
            )
            for task in tasks
        }
        materials = self._material_requirement_service.list_requirements(work_order_id=work_order.id)
        documents = (
            self._document_service.list_documents_for_entity(
                entity_type="work_order",
                entity_id=work_order.id,
                active_only=None,
            )
            if self._document_service is not None
            else []
        )

        self._detail_tasks_by_id = {task.id: task for task in tasks}
        self._detail_steps_by_id = {}
        self._step_ids_by_task_id = {}
        self._detail_labor_entries_by_task_id = {}
        for task in tasks:
            step_ids: list[str] = []
            for step in step_rows_by_task_id.get(task.id, []):
                self._detail_steps_by_id[step.id] = step
                step_ids.append(step.id)
            self._step_ids_by_task_id[task.id] = step_ids
            if self._labor_service is not None:
                self._detail_labor_entries_by_task_id[task.id] = self._labor_service.list_task_labor_entries(task.id)
            else:
                self._detail_labor_entries_by_task_id[task.id] = []
        self._detail_documents_by_id = {document.id: document for document in documents}

        self.title_label.setText(
            f"{work_order.work_order_code} - {work_order.title or work_order.work_order_type.value.replace('_', ' ').title()}"
        )
        self.overview_summary.setText(
            "\n".join(
                [
                    f"Type: {work_order.work_order_type.value.replace('_', ' ').title()} | Status: {work_order.status.value.replace('_', ' ').title()} | Priority: {work_order.priority.value.title()}",
                    f"Site: {self._site_labels.get(work_order.site_id, work_order.site_id)}",
                    f"Asset: {self._label_for(self._asset_labels, work_order.asset_id)} | System: {self._label_for(self._system_labels, work_order.system_id)}",
                    f"Location: {self._label_for(self._location_labels, work_order.location_id)} | Component: {work_order.component_id or '-'}",
                    f"Assigned: {self._format_assignment(work_order.assigned_employee_id, work_order.assigned_team_id)} | Planner: {work_order.planner_user_id or '-'} | Supervisor: {work_order.supervisor_user_id or '-'}",
                    f"Source: {self._source_label(work_order.source_type, work_order.source_id)}",
                    f"Plan window: {self._format_timestamp_pair(work_order.planned_start, work_order.planned_end)}",
                    f"Actual window: {self._format_timestamp_pair(work_order.actual_start, work_order.actual_end)}",
                    f"Failure / Root cause: {work_order.failure_code or '-'} / {work_order.root_cause_code or '-'}",
                    f"Downtime: {work_order.downtime_minutes or 0} min",
                    f"Evidence: {len(documents)} linked document(s)",
                    f"Notes: {work_order.notes or '-'}",
                ]
            )
        )
        self._populate_task_table(tasks, step_rows_by_task_id=step_rows_by_task_id, selected_task_id=selected_task_id)
        selected_task = self._selected_task()
        effective_task_id = selected_task.id if selected_task is not None else selected_task_id
        self._populate_step_table(selected_task_id=effective_task_id, selected_step_id=selected_step_id)
        self._populate_labor_table(selected_task_id=effective_task_id)
        self._populate_material_table(materials)
        self._populate_evidence_table(documents)
        self.workbench.set_current_section("overview")

    def _populate_task_table(self, tasks, *, step_rows_by_task_id, selected_task_id: str | None) -> None:
        self.task_table.blockSignals(True)
        self.task_table.setRowCount(len(tasks))
        selected_row = 0 if tasks else -1
        for row_index, task in enumerate(tasks):
            step_rows = step_rows_by_task_id.get(task.id, [])
            done_steps = sum(1 for row in step_rows if row.status.value == "DONE")
            values = (
                f"{task.sequence_no}. {task.task_name}",
                self._format_assignment(task.assigned_employee_id, task.assigned_team_id),
                task.status.value.replace("_", " ").title(),
                task.required_skill or "-",
                self._format_task_minutes(task),
                self._format_step_summary(task.status, done_steps, len(step_rows)),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(_TASK_ID_ROLE, task.id)
                self.task_table.setItem(row_index, column, item)
            if selected_task_id and task.id == selected_task_id:
                selected_row = row_index
        if selected_row >= 0:
            self.task_table.selectRow(selected_row)
        else:
            self.task_table.clearSelection()
        self.task_table.blockSignals(False)
        self._sync_task_actions()

    def _populate_step_table(self, *, selected_task_id: str | None, selected_step_id: str | None) -> None:
        selected_task = self._detail_tasks_by_id.get(selected_task_id or "")
        step_rows = list(self._steps_for_selected_task(selected_task_id))
        self.step_table.blockSignals(True)
        self.step_table.setRowCount(len(step_rows))
        selected_row = 0 if step_rows else -1
        for row_index, step in enumerate(step_rows):
            values = (
                f"{step.step_number}. {step.instruction}",
                step.status.value.replace("_", " ").title(),
                self._format_step_requirements(step),
                self._format_step_completion(step),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(_STEP_ID_ROLE, step.id)
                self.step_table.setItem(row_index, column, item)
            if selected_step_id and step.id == selected_step_id:
                selected_row = row_index
        if selected_row >= 0:
            self.step_table.selectRow(selected_row)
        else:
            self.step_table.clearSelection()
        self.step_table.blockSignals(False)
        if selected_task is None:
            self.step_summary.setText("Select a task to review and execute its steps.")
        else:
            self.step_summary.setText(
                f"Current task: {selected_task.sequence_no}. {selected_task.task_name}. Execute or confirm its steps here."
            )
        self._sync_step_actions()

    def _populate_material_table(self, materials) -> None:
        self.material_table.setRowCount(len(materials))
        for row_index, requirement in enumerate(materials):
            values = (
                requirement.description or requirement.stock_item_id or "-",
                f"{requirement.required_qty} {requirement.required_uom}",
                f"{requirement.issued_qty} {requirement.required_uom}",
                requirement.procurement_status.value.replace("_", " ").title(),
                "Stock" if requirement.is_stock_item else "Direct",
            )
            for column, value in enumerate(values):
                self.material_table.setItem(row_index, column, QTableWidgetItem(value))

    def _populate_labor_table(self, *, selected_task_id: str | None) -> None:
        task = self._detail_tasks_by_id.get(selected_task_id or "")
        entries = list(self._detail_labor_entries_by_task_id.get(selected_task_id or "", []))
        self.labor_table.setRowCount(len(entries))
        for row_index, entry in enumerate(entries):
            values = (
                entry.entry_date.isoformat(),
                f"{entry.hours:.2f}",
                entry.author_username or entry.author_user_id or "system",
                entry.note or "-",
            )
            for column, value in enumerate(values):
                self.labor_table.setItem(row_index, column, QTableWidgetItem(value))
        if task is None:
            self.labor_summary.setText("Select a task to review or book labor.")
        elif not (task.assigned_employee_id or "").strip():
            self.labor_summary.setText(
                f"Task {task.sequence_no} has no assigned employee yet. Assign one before booking labor."
            )
        else:
            total_hours = sum(float(entry.hours or 0.0) for entry in entries)
            self.labor_summary.setText(
                f"Task {task.sequence_no} is assigned to {self._format_assignment(task.assigned_employee_id, task.assigned_team_id)}. "
                f"{len(entries)} entry(s) logged, {total_hours:.2f} hour(s) total."
            )
        self._sync_labor_actions()

    def _populate_evidence_table(self, documents) -> None:
        self.evidence_table.blockSignals(True)
        self.evidence_table.setRowCount(len(documents))
        for row_index, document in enumerate(documents):
            values = (
                f"{document.document_code} - {document.title}",
                document.document_type.value.replace("_", " ").title(),
                document.document_structure_id or "-",
                format_timestamp(document.uploaded_at),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, document.id)
                self.evidence_table.setItem(row_index, column, item)
        if documents:
            self.evidence_table.selectRow(0)
        else:
            self.evidence_table.clearSelection()
        self.evidence_table.blockSignals(False)
        self._sync_evidence_actions()

    def _selected_task_id(self) -> str | None:
        row = self.task_table.currentRow()
        if row < 0:
            return None
        item = self.task_table.item(row, 0)
        if item is None:
            return None
        value = item.data(_TASK_ID_ROLE)
        return str(value) if value else None

    def _selected_step_id(self) -> str | None:
        row = self.step_table.currentRow()
        if row < 0:
            return None
        item = self.step_table.item(row, 0)
        if item is None:
            return None
        value = item.data(_STEP_ID_ROLE)
        return str(value) if value else None

    def _selected_task(self):
        task_id = self._selected_task_id()
        return self._detail_tasks_by_id.get(task_id or "")

    def _selected_step(self):
        step_id = self._selected_step_id()
        return self._detail_steps_by_id.get(step_id or "")

    def _selected_evidence_document(self):
        row = self.evidence_table.currentRow()
        if row < 0:
            return None
        item = self.evidence_table.item(row, 0)
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        if not value:
            return None
        return self._detail_documents_by_id.get(str(value))

    def _steps_for_selected_task(self, task_id: str | None):
        if not task_id:
            return []
        return [
            self._detail_steps_by_id[step_id]
            for step_id in self._step_ids_by_task_id.get(task_id, [])
            if step_id in self._detail_steps_by_id
        ]

    def _task_can_complete(self, task) -> bool:
        if task is None:
            return False
        if task.status not in {
            MaintenanceWorkOrderTaskStatus.NOT_STARTED,
            MaintenanceWorkOrderTaskStatus.IN_PROGRESS,
        }:
            return False
        if task.completion_rule != MaintenanceTaskCompletionRule.ALL_STEPS_REQUIRED:
            return True
        step_ids = self._step_ids_by_task_id.get(task.id, [])
        if not step_ids:
            return False
        for step_id in step_ids:
            step = self._detail_steps_by_id.get(step_id)
            if step is None or step.status != MaintenanceWorkOrderTaskStepStatus.DONE:
                return False
            if step.requires_confirmation and step.confirmed_at is None:
                return False
            if step.requires_measurement and not str(step.measurement_value or "").strip():
                return False
        return True

    def _sync_step_measurement_editor(self, step) -> None:
        if step is None:
            self.step_measurement_edit.clear()
            self.step_measurement_edit.setPlaceholderText("Enter measurement if the selected step requires one")
            return
        if step.requires_measurement or step.measurement_value:
            unit = f" ({step.measurement_unit})" if step.measurement_unit else ""
            self.step_measurement_edit.setPlaceholderText(f"Measurement{unit}")
            self.step_measurement_edit.setText(step.measurement_value or "")
            return
        self.step_measurement_edit.clear()
        self.step_measurement_edit.setPlaceholderText("Selected step does not require a measurement")

    def _sync_task_actions(self) -> None:
        task = self._selected_task()
        if task is None:
            self.task_summary.setText("No task selected.")
            self.btn_complete_task.setEnabled(False)
            return
        self.task_summary.setText(
            f"Selected task {task.sequence_no} is {task.status.value.replace('_', ' ').title()} and assigned to {self._format_assignment(task.assigned_employee_id, task.assigned_team_id)}."
        )
        self.btn_complete_task.setEnabled(self._task_can_complete(task))

    def _sync_step_actions(self) -> None:
        task = self._selected_task()
        step = self._selected_step()
        self._sync_step_measurement_editor(step)
        if step is None:
            self.btn_start_step.setEnabled(False)
            self.btn_done_step.setEnabled(False)
            self.btn_confirm_step.setEnabled(False)
            return
        self.btn_start_step.setEnabled(
            step.status in {
                MaintenanceWorkOrderTaskStepStatus.NOT_STARTED,
                MaintenanceWorkOrderTaskStepStatus.FAILED,
            }
        )
        self.btn_done_step.setEnabled(
            step.status in {
                MaintenanceWorkOrderTaskStepStatus.NOT_STARTED,
                MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS,
            }
        )
        self.btn_confirm_step.setEnabled(
            step.requires_confirmation
            and step.status == MaintenanceWorkOrderTaskStepStatus.DONE
            and step.confirmed_at is None
        )
        if task is not None:
            self.step_summary.setText(
                f"Task {task.sequence_no}: execute step {step.step_number} ({step.status.value.replace('_', ' ').title()})."
            )

    def _sync_evidence_actions(self) -> None:
        self.btn_preview_evidence.setEnabled(self._selected_evidence_document() is not None)

    def _sync_labor_actions(self) -> None:
        task = self._selected_task()
        can_book = (
            self._labor_service is not None
            and task is not None
            and bool((task.assigned_employee_id or "").strip())
        )
        self.btn_add_labor.setEnabled(can_book)

    def _on_task_selection_changed(self) -> None:
        self._populate_step_table(
            selected_task_id=self._selected_task_id(),
            selected_step_id=None,
        )
        self._populate_labor_table(selected_task_id=self._selected_task_id())
        self._sync_task_actions()

    def _on_step_selection_changed(self) -> None:
        self._sync_step_actions()

    def _refresh_after_action(self, *, selected_task_id: str | None, selected_step_id: str | None) -> None:
        if self._current_work_order_id is None:
            return
        self.load_work_order(
            self._current_work_order_id,
            selected_task_id=selected_task_id,
            selected_step_id=selected_step_id,
        )

    def _on_complete_task(self) -> None:
        task = self._selected_task()
        if task is None:
            QMessageBox.information(self, "Maintenance Work Order Detail", "Select a task to complete it.")
            return
        updated = self._work_order_task_service.update_task(
            task.id,
            status=MaintenanceWorkOrderTaskStatus.COMPLETED.value,
            expected_version=task.version,
        )
        self._refresh_after_action(selected_task_id=updated.id, selected_step_id=None)
        self.workbench.set_current_section("tasks")

    def _on_start_step(self) -> None:
        step = self._selected_step()
        task = self._selected_task()
        if step is None or task is None:
            QMessageBox.information(self, "Maintenance Work Order Detail", "Select a task step to start execution.")
            return
        updated = self._work_order_task_step_service.update_step(
            step.id,
            status=MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS.value,
            expected_version=step.version,
        )
        self._refresh_after_action(selected_task_id=task.id, selected_step_id=updated.id)
        self.workbench.set_current_section("steps")

    def _on_done_step(self) -> None:
        step = self._selected_step()
        task = self._selected_task()
        if step is None or task is None:
            QMessageBox.information(self, "Maintenance Work Order Detail", "Select a task step to complete it.")
            return
        update_kwargs = {
            "status": MaintenanceWorkOrderTaskStepStatus.DONE.value,
            "expected_version": step.version,
        }
        if self.step_measurement_edit.text().strip():
            update_kwargs["measurement_value"] = self.step_measurement_edit.text().strip()
        updated = self._work_order_task_step_service.update_step(step.id, **update_kwargs)
        self._refresh_after_action(selected_task_id=task.id, selected_step_id=updated.id)
        self.workbench.set_current_section("steps")

    def _on_confirm_step(self) -> None:
        step = self._selected_step()
        task = self._selected_task()
        if step is None or task is None:
            QMessageBox.information(self, "Maintenance Work Order Detail", "Select a completed task step to confirm it.")
            return
        updated = self._work_order_task_step_service.update_step(
            step.id,
            confirm_completion=True,
            expected_version=step.version,
        )
        self._refresh_after_action(selected_task_id=task.id, selected_step_id=updated.id)
        self.workbench.set_current_section("steps")

    def _on_add_labor_entry(self) -> None:
        task = self._selected_task()
        if task is None or self._labor_service is None:
            QMessageBox.information(self, "Maintenance Work Order Detail", "Select a task to add labor.")
            return
        entry = self._labor_service.add_task_labor_entry(
            work_order_task_id=task.id,
            entry_date=self.labor_date_edit.date().toPython(),
            hours=float(self.labor_hours_spin.value()),
            note=self.labor_note_edit.text().strip(),
        )
        self.labor_note_edit.clear()
        self._refresh_after_action(selected_task_id=task.id, selected_step_id=self._selected_step_id())
        self.workbench.set_current_section("labor")
        self.labor_date_edit.setDate(QDate(entry.entry_date.year, entry.entry_date.month, entry.entry_date.day))

    def _show_evidence_preview(self) -> None:
        document = self._selected_evidence_document()
        if document is None:
            QMessageBox.information(self, "Maintenance Work Order Detail", "Select a linked evidence document to preview it.")
            return
        DocumentPreviewDialog(document=document, parent=self).exec()

    def _source_label(self, source_type: str, source_id: str | None) -> str:
        if not source_id:
            return source_type.replace("_", " ").title()
        if source_type == "WORK_REQUEST" and self._work_request_service is not None:
            try:
                request = self._work_request_service.get_work_request(source_id)
            except Exception:  # noqa: BLE001
                return f"{source_type.replace('_', ' ').title()}: {source_id}"
            return f"Work Request: {request.work_request_code}"
        return f"{source_type.replace('_', ' ').title()}: {source_id}"

    @staticmethod
    def _label_for(labels: dict[str, str], value: str | None) -> str:
        if not value:
            return "-"
        return labels.get(value, value)

    @staticmethod
    def _format_timestamp_pair(start, end) -> str:
        if start is None and end is None:
            return "-"
        if start is None:
            return f"Until {format_timestamp(end)}"
        if end is None:
            return f"From {format_timestamp(start)}"
        return f"{format_timestamp(start)} -> {format_timestamp(end)}"

    @staticmethod
    def _format_task_minutes(task) -> str:
        estimated = task.estimated_minutes if task.estimated_minutes is not None else "-"
        actual = task.actual_minutes if task.actual_minutes is not None else "-"
        return f"{estimated} / {actual}"

    @staticmethod
    def _format_step_summary(task_status: MaintenanceWorkOrderTaskStatus, done_steps: int, total_steps: int) -> str:
        if total_steps == 0:
            return "No steps"
        if task_status == MaintenanceWorkOrderTaskStatus.COMPLETED:
            return f"{done_steps}/{total_steps} done"
        return f"{done_steps}/{total_steps} complete"

    @staticmethod
    def _format_assignment(assigned_employee_id: str | None, assigned_team_id: str | None) -> str:
        if assigned_employee_id:
            return f"Employee {assigned_employee_id}"
        if assigned_team_id:
            return f"Team {assigned_team_id}"
        return "Unassigned"

    @staticmethod
    def _format_step_requirements(step) -> str:
        flags = []
        if step.requires_confirmation:
            flags.append("Confirm")
        if step.requires_measurement:
            unit = f" {step.measurement_unit}" if step.measurement_unit else ""
            flags.append(f"Measure{unit}")
        if step.requires_photo:
            flags.append("Photo")
        return ", ".join(flags) if flags else "Standard"

    @staticmethod
    def _format_step_completion(step) -> str:
        parts = []
        if step.completed_at is not None:
            completed_by = f" by {step.completed_by_user_id}" if step.completed_by_user_id else ""
            parts.append(f"Done {format_timestamp(step.completed_at)}{completed_by}")
        if step.confirmed_at is not None:
            confirmed_by = f" by {step.confirmed_by_user_id}" if step.confirmed_by_user_id else ""
            parts.append(f"Confirmed {format_timestamp(step.confirmed_at)}{confirmed_by}")
        if step.measurement_value:
            measurement_unit = f" {step.measurement_unit}" if step.measurement_unit else ""
            parts.append(f"Measurement {step.measurement_value}{measurement_unit}")
        return " | ".join(parts) if parts else "-"

    @staticmethod
    def _resize_to_contents():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.ResizeToContents

    @staticmethod
    def _stretch():
        from PySide6.QtWidgets import QHeaderView

        return QHeaderView.Stretch


__all__ = ["MaintenanceWorkOrderDetailDialog"]
