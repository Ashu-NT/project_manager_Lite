from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.models import CostType, Resource
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.cost.models import LaborPlanVsActualTableModel
from ui.styles.formatting import currency_symbol_from_code, fmt_currency
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class ResourceLaborDialog(QDialog):
    def __init__(
        self,
        parent,
        project_id: str,
        reporting_service: ReportingService,
        task_service: TaskService,
        resource_service: ResourceService,
    ):
        super().__init__(parent)
        self.setWindowTitle("Labor cost details")
        self._project_id: str = project_id
        self._reporting_service: ReportingService = reporting_service
        self._task_service: TaskService = task_service
        self._resource_service: ResourceService = resource_service

        self.table = QTableView()
        self._model: LaborPlanVsActualTableModel | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.setMinimumSize(self.sizeHint())
        self.setMinimumWidth(CFG.MIN_DEPENDENCIES_WIDTH)

        self.lbl_overview = QLabel("")
        self.lbl_overview.setWordWrap(True)
        self.lbl_note = QLabel("")
        self.lbl_note.setWordWrap(True)
        self.lbl_note.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        layout.addWidget(self.lbl_overview)
        layout.addWidget(self.lbl_note)
        layout.addWidget(QLabel(CFG.LABOR_PER_RESOURCE_TITLE))
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        self.btn_show_assignments = QPushButton(CFG.SHOW_ASSIGNMENTS_BUTTON_LABEL)
        self.btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        self.btn_show_assignments.clicked.connect(self.show_selected_assignments)
        self.btn_close.clicked.connect(self.accept)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_show_assignments)
        btn_row.addWidget(self.btn_close)
        layout.addLayout(btn_row)

        self.reload()

    def reload(self):
        rows = self._reporting_service.get_project_labor_plan_vs_actual(self._project_id)

        resource_count = len(rows)
        total_actual_cost = 0.0
        total_actual_hours = 0.0

        totals_by_currency_planned: dict[str, float] = {}
        totals_by_currency_actual: dict[str, float] = {}

        for row in rows:
            cur_p = (row.planned_currency_code or "").upper() or "-"
            cur_a = (row.actual_currency_code or "").upper() or cur_p or "-"
            totals_by_currency_planned[cur_p] = totals_by_currency_planned.get(cur_p, 0.0) + float(row.planned_cost or 0.0)
            totals_by_currency_actual[cur_a] = totals_by_currency_actual.get(cur_a, 0.0) + float(row.actual_cost or 0.0)

            total_actual_cost += float(row.actual_cost or 0.0)
            total_actual_hours += float(row.actual_hours or 0.0)

        def _fmt_totals(totals: dict[str, float]) -> str:
            parts = []
            for cur, amt in totals.items():
                sym = currency_symbol_from_code(cur)
                parts.append(fmt_currency(amt, sym) if sym else f"{cur} {fmt_currency(amt, '')}".strip())
            return "; ".join(parts)

        self.lbl_overview.setText(
            f"{resource_count} resources | Actual: {total_actual_hours:.2f} hrs | "
            f"Planned totals: {_fmt_totals(totals_by_currency_planned)} | "
            f"Actual totals: {_fmt_totals(totals_by_currency_actual)}"
        )

        note = ""
        try:
            parent = self.parent()
            cost_service = getattr(parent, "_cost_service", None)
            if cost_service is not None:
                costs = cost_service.list_cost_items_for_project(self._project_id)
                manual_labor_exists = any(getattr(c, "cost_type", None) == CostType.LABOR for c in costs)
                if manual_labor_exists and total_actual_cost > 0:
                    note = CFG.LABOR_IGNORED_NOTE
        except Exception:
            note = ""
        self.lbl_note.setText(note)

        self._model = LaborPlanVsActualTableModel(rows)
        self.table.setModel(self._model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)

    def show_selected_assignments(self):
        sel = self.table.selectionModel().selectedRows()
        if not sel:
            QMessageBox.information(self, "Assignments", "Please select a resource.")
            return
        row = sel[0].row()
        model_row = self._model.get_row(row)
        if not model_row:
            QMessageBox.warning(self, "Assignments", "Failed to locate resource.")
            return

        resources = self._resource_service.list_resources()
        res_obj = next((x for x in resources if x.id == model_row.resource_id), None)
        if not res_obj:
            QMessageBox.warning(self, "Assignments", "Resource object not found.")
            return

        project_name = ""
        try:
            parent = self.parent()
            project = getattr(parent, "_current_project", None)
            project_name = project.name if project else self._project_id
        except Exception:
            project_name = self._project_id

        dlg = ResourceAssignmentsDialog(
            self,
            task_service=self._task_service,
            reporting_service=self._reporting_service,
            project_id=self._project_id,
            project_name=project_name,
            resource=res_obj,
        )
        dlg.exec()

        self.reload()
        self.reload_costs()

    def reload_costs(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "reload_costs"):
            parent.reload_costs()


class ResourceAssignmentsDialog(QDialog):
    """
    Read-only view of selected resource assignments in the project.
    """

    def __init__(
        self,
        parent,
        task_service: TaskService,
        reporting_service: ReportingService,
        project_id: str,
        project_name: str,
        resource: Resource,
    ):
        super().__init__(parent)
        self.setWindowTitle(f"{resource.name} - assignments in {project_name}")
        self._task_service: TaskService = task_service
        self._reporting_service: ReportingService = reporting_service
        self._project_id: str = project_id
        self._project_name: str = project_name
        self._resource: Resource = resource

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Task", "Allocation %", "Hours logged", "Cost"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)

        self.lbl_totals = QLabel("")
        self.lbl_totals.setWordWrap(True)
        self.lbl_totals.setStyleSheet(CFG.NOTE_STYLE_SHEET)

        btn_close = QPushButton(CFG.CLOSE_BUTTON_LABEL)
        btn_close.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        btn_close.setFixedHeight(CFG.BUTTON_HEIGHT)
        btn_close.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        layout.addWidget(self.table)
        layout.addWidget(self.lbl_totals)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(btn_close)
        layout.addLayout(row)

        self.reload()

    def reload(self):
        labor_rows = self._reporting_service.get_project_labor_details(self._project_id)

        rr = next((x for x in labor_rows if x.resource_id == self._resource.id), None)
        if not rr:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No assignments found"))
            for c in range(1, self.table.columnCount()):
                self.table.setItem(0, c, QTableWidgetItem(""))
            self.lbl_totals.setText("")
            return

        assigns = rr.assignments or []
        self.table.setRowCount(len(assigns))

        total_hours = 0.0
        total_cost = 0.0
        cur = (rr.currency_code or "").upper()

        from PySide6.QtCore import Qt as _Qt

        for i, assignment in enumerate(assigns):
            self.table.setItem(i, 0, QTableWidgetItem(assignment.task_name))

            alloc = 0.0
            try:
                obj = self._task_service.get_assignment(assignment.assignment_id)
                alloc = float(getattr(obj, "allocation_percent", 0.0) or 0.0) if obj else 0.0
            except Exception:
                alloc = 0.0

            it_alloc = QTableWidgetItem(f"{alloc:.1f}")
            it_alloc.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.table.setItem(i, 1, it_alloc)

            it_h = QTableWidgetItem(f"{float(assignment.hours or 0.0):.2f}")
            it_h.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.table.setItem(i, 2, it_h)

            sym = currency_symbol_from_code(assignment.currency_code or cur)
            it_cost = QTableWidgetItem(fmt_currency(float(assignment.cost or 0.0), sym))
            it_cost.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.table.setItem(i, 3, it_cost)

            total_hours += float(assignment.hours or 0.0)
            total_cost += float(assignment.cost or 0.0)
            if not cur and assignment.currency_code:
                cur = (assignment.currency_code or "").upper()

        sym = currency_symbol_from_code(cur)
        self.lbl_totals.setText(
            f"Total hours: {total_hours:.2f} hrs | Total cost: {fmt_currency(total_cost, sym)}"
        )

        self.table.resizeRowsToContents()


__all__ = ["ResourceLaborDialog", "ResourceAssignmentsDialog"]
