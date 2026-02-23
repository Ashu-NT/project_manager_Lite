# ui/cost/tab.py
from __future__ import annotations
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QPushButton,
    QTableView, QTableWidget, QTableWidgetItem, QDialog, QMessageBox, QGroupBox
)

from core.services.project import ProjectService
from core.services.task import TaskService
from core.services.cost import CostService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.exceptions import ValidationError, NotFoundError
from core.models import Project, Task, CostItem, CostType

from ui.styles.formatting import fmt_currency, currency_symbol_from_code
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from core.events.domain_events import domain_events
from .components import (
    CostTableModel,
    CostEditDialog,
    ResourceLaborDialog,
)

class CostTab(QWidget):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        cost_service: CostService,
        reporting_service: ReportingService,
        resource_service: ResourceService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service = project_service
        self._task_service = task_service
        self._cost_service = cost_service
        self._reporting_service = reporting_service
        self._resource_service = resource_service

        self._current_project: Project | None = None
        self._project_tasks: list[Task] = []

        self._setup_ui()
        self._load_projects()
        domain_events.costs_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.tasks_changed.connect(self._on_costs_or_tasks_changed)
        domain_events.project_changed.connect(self._on_project_changed_event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())
        
        # Top row: project select and refresh
        top = QHBoxLayout()
        top.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        
        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addStretch()
        layout.addLayout(top)

        # Toolbar: New / Edit / Delete / Refresh
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_COST_ITEM_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_labor_details = QPushButton(CFG.LABOR_DETAILS_BUTTON_LABEL)
        self.btn_refresh_costs = QPushButton(CFG.REFRESH_COSTS_LABEL)
        
        for btn in (
            self.btn_reload_projects,
            self.btn_new, 
            self.btn_edit, 
            self.btn_delete, 
            self.btn_refresh_costs
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        
        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh_costs)
        layout.addLayout(toolbar)
        
        #-------- Budget/ Planned / Acutual summary area --------#
        self.grp_budget = QGroupBox("Budget Summary")
        self.grp_budget.setFont(CFG.GROUPBOX_TITLE_FONT)
        
        self.lbl_budget_summary = QLabel("")
        self.lbl_budget_summary.setWordWrap(True)
        self.lbl_budget_summary.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        
        g = QGridLayout()
        g.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        g.addWidget(self.lbl_budget_summary, 0, 0)
        
        self.grp_budget.setLayout(g)
        layout.addWidget(self.grp_budget)

        # Labor summary frame 
        self.tbl_labor_summary = QTableWidget()
        # columns: Resource, Task, Hours, Rate, Currency, Cost
        self.tbl_labor_summary.setColumnCount(len(CFG.LABOR_SUMMARY_HEADERS))
        self.tbl_labor_summary.setHorizontalHeaderLabels(CFG.LABOR_SUMMARY_HEADERS)
        self.tbl_labor_summary.verticalHeader().setVisible(False)
        self.tbl_labor_summary.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tbl_labor_summary.setSelectionMode(QTableWidget.NoSelection)
        self.tbl_labor_summary.horizontalHeader().setStretchLastSection(True)
        # let the height adapt to rows; set a reasonable minimum
        self.tbl_labor_summary.setMinimumHeight(80)
        self.tbl_labor_summary.setSizePolicy(CFG.INPUT_POLICY)
        style_table(self.tbl_labor_summary) 
        # align numeric columns to right when populating rows

        # ensure button sizing matches other toolbar buttons
        self.btn_labor_details.setText(CFG.LABOR_DETAILS_BUTTON_LABEL)
        self.btn_labor_details.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_labor_details.setFixedHeight(CFG.BUTTON_HEIGHT)

        self.grp_labor = QGroupBox(CFG.LABOR_GROUP_TITLE)
        self.grp_labor.setFont(CFG.GROUPBOX_TITLE_FONT)
        
        grid = QGridLayout()
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)
        grid.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD) 

        # summary table sits at (0,0); details button at (0,1)
        grid.addWidget(self.tbl_labor_summary, 0, 0)
        grid.addWidget(self.btn_labor_details, 0, 1, alignment=Qt.AlignTop)

        # add a dedicated note label under the summary that spans both columns
        self.lbl_labor_note = QLabel("")
        self.lbl_labor_note.setWordWrap(True)
        self.lbl_labor_note.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        grid.addWidget(self.lbl_labor_note, 1, 0, 1, 2)

        self.grp_labor.setLayout(grid)
        layout.addWidget(self.grp_labor)

        # Table of costs
        self.table = QTableView()
        self.model = CostTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        layout.addWidget(self.table)

        # Signals
        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_costs.clicked.connect(self.reload_costs)
        self.btn_new.clicked.connect(self.create_cost_item)
        self.btn_edit.clicked.connect(self.edit_cost_item)
        self.btn_delete.clicked.connect(self.delete_cost_item)
        self.btn_labor_details.clicked.connect(self.show_labor_details)
        self.tbl_labor_summary.itemSelectionChanged.connect(self._on_labor_table_selected)
      

    # ---------------- Helper methods ---------------- #

    def _load_projects(self):
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            # store Project object or id
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)

        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
            self._on_project_changed(0)

    def _on_costs_or_tasks_changed(self, project_id: str):
        pid = self._current_project_id()
        if pid != project_id:
            return  # ignore events for other projects
        # If tasks changed, update the internal task list (task name mapping)
        self._project_tasks = self._task_service.list_tasks_for_project(pid)
        # Also refresh the current Project object (for any changes in budget/currency if needed)
        self._current_project = self._project_service.get_project(pid)
        # Now reload the costs and related summaries for this project
        self.reload_costs()

    def _on_project_changed_event(self, project_id: str):
        prev_pid = self._current_project_id()
        projects = self._project_service.list_projects()
        # Reload project combo box
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
        # Preserve selection if possible
        if prev_pid and prev_pid in [p.id for p in projects]:
            idx = self.project_combo.findData(prev_pid)
            if idx != -1:
                self.project_combo.setCurrentIndex(idx)
        else:
            # Select first project by default if current no longer valid
            if self.project_combo.count() > 0:
                self.project_combo.setCurrentIndex(0)
        # Update current project reference and related data
        pid = self._current_project_id()
        self._current_project = self._project_service.get_project(pid) if pid else None
        self._project_tasks = self._task_service.list_tasks_for_project(pid) if pid else []
        self.reload_costs()        

    def _current_project_id(self) -> Optional[str]:
        idx = self.project_combo.currentIndex()
        if idx < 0:
            return None
        return self.project_combo.itemData(idx)

    def _load_tasks_for_current_project(self):
        pid = self._current_project_id()
        if not pid:
            self._project_tasks = []
            return
        self._project_tasks = self._task_service.list_tasks_for_project(pid)

    def _on_project_changed(self, index: int):
        pid = self._current_project_id()
        if not pid:
            self._current_project = None
            self._project_tasks = []
            self.model.set_costs([], {})
            return
        # fetch project object if you need it
        projects = self._project_service.list_projects()
        self._current_project = next((p for p in projects if p.id == pid), None)
        self._load_tasks_for_current_project()
        tasks_by_id = {t.id:t for t in self._project_tasks}
        project_currency = self._current_project.currency if self._current_project else ""
        self.model.set_context(tasks_by_id,project_currency)
        
        self.reload_costs()

    def reload_costs(self):
        pid = self._current_project_id()
        if not pid:
            self.model.set_costs([], {})
            # clear the labor summary table and note
            self.tbl_labor_summary.setRowCount(0)
            self.lbl_labor_note.setText("")
            return

        costs = self._cost_service.list_cost_items_for_project(pid)
        task_names = {t.id: t.name for t in self._project_tasks}

        # keep context fresh
        tasks_by_id = {t.id: t for t in self._project_tasks}
        project_currency = self._current_project.currency if self._current_project else ""
        self.model.set_context(tasks_by_id, project_currency)

        self.model.set_costs(costs, task_names)

        # ------ budget summary -------
        try:
            row = self._reporting_service.get_cost_breakdown(pid)
            planed_total = sum(float(r.planned or 0.0) for r in row)
            actual_total = sum(float(r.actual or 0.0) for r in row)
            
            budget = float(getattr(self._current_project, 'planned_budget', 0.0) or 0.0)
            cur = (getattr(self._current_project, 'currency', '') or '').upper() if self._current_project else ""
            sym = currency_symbol_from_code(cur)
            
            # remaining based on plan + actual cost
            rem_plan = budget - planed_total
            rem_actual = budget - actual_total
            
            # Text block
            lines = []
            if budget > 0:
                lines.append(f"Budget: {fmt_currency(budget, sym)}")
                lines.append(f"Total Planned Cost: {fmt_currency(planed_total, sym)} (Remaining vs plan: {fmt_currency(rem_plan,sym)})")
                lines.append(f"Total Actual Cost: {fmt_currency(actual_total, sym)} (Remaining vs plan: {fmt_currency(rem_actual,sym)})")
                if planed_total > budget:
                    lines.append("Planned total exceeds budget.")
            else:
                lines.append(f"Total Planned Cost: {fmt_currency(planed_total, sym)}")
                lines.append(f"Total Actual Cost: {fmt_currency(actual_total, sym)}")
                lines.append("Note: set project budget to track remaining budget.")
                
            self.lbl_budget_summary.setText("\n".join(lines))
        except Exception:
            self.lbl_budget_summary.setText("")
       
       
        # reload labor summary
        try:
            self.reload_labor_summary(pid)
        except Exception:
            # Fail silently and clear the labor summary table/note if reporting fails
            self.tbl_labor_summary.setRowCount(0)
            self.lbl_labor_note.setText("")

    def _get_selected_cost(self) -> Optional[CostItem]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_cost(row)

    # ---------------- Labor helpers ---------------- #
    def reload_labor_summary(self, project_id: str):
        details = self._reporting_service.get_project_labor_details(project_id)
        # start by clearing the table
        self.tbl_labor_summary.setRowCount(0)
        if not details:
            # show a simple 'none' row
            self.tbl_labor_summary.setRowCount(1)
            self.tbl_labor_summary.setItem(0, 0, QTableWidgetItem(CFG.NO_LABOR_ASSIGNMENTS_TEXT))
            for c in range(1, self.tbl_labor_summary.columnCount()):
                self.tbl_labor_summary.setItem(0, c, QTableWidgetItem(""))
            self.lbl_labor_note.setText("")
            return

        # build assignment rows (one row per assignment)
        rows_data = []
        totals_by_currency: dict[str, float] = {}
        total_hours = 0.0
        for r in details:
            for a in r.assignments:
                rows_data.append({
                    "resource_name": r.resource_name,
                    "task_name": a.task_name,
                    "hours": float(a.hours or 0.0),
                    "hourly_rate": float(a.hourly_rate or 0.0),
                    "currency": (a.currency_code or (r.currency_code or (self._current_project.currency if self._current_project else "")) or "").upper(),
                    "cost": float(a.cost or 0.0),
                })
                total_hours += float(a.hours or 0.0)
                cur = (a.currency_code or (r.currency_code or (self._current_project.currency if self._current_project else "")) or "").upper()
                totals_by_currency[cur] = totals_by_currency.get(cur, 0.0) + float(a.cost or 0.0)

        # detect manual labor cost items; show explanatory note when both exist
        try:
            costs = self._cost_service.list_cost_items_for_project(project_id)
            manual_labor_exists = any(getattr(c, 'cost_type', None) == CostType.LABOR for c in costs)
        except Exception:
            manual_labor_exists = False

        note = CFG.LABOR_IGNORED_NOTE if (manual_labor_exists and any(amt > 0 for amt in totals_by_currency.values())) else ""

        # populate table: assignment rows
        base_rows = len(rows_data)
        total_rows = base_rows + 1 + len(totals_by_currency)  # +1 for total hours row, + per-currency totals
        self.tbl_labor_summary.setRowCount(total_rows)

        from PySide6.QtCore import Qt as _Qt
        row = 0
        for rdata in rows_data:
            self.tbl_labor_summary.setItem(row, 0, QTableWidgetItem(rdata["resource_name"]))
            self.tbl_labor_summary.setItem(row, 1, QTableWidgetItem(rdata["task_name"]))
            item_h = QTableWidgetItem(f"{rdata['hours']:.2f}")
            item_h.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.tbl_labor_summary.setItem(row, 2, item_h)
            item_rate = QTableWidgetItem(fmt_currency(rdata['hourly_rate'], currency_symbol_from_code(rdata['currency'])))
            item_rate.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.tbl_labor_summary.setItem(row, 3, item_rate)
            self.tbl_labor_summary.setItem(row, 4, QTableWidgetItem(rdata['currency'] or ""))
            item_cost = QTableWidgetItem(fmt_currency(rdata['cost'], currency_symbol_from_code(rdata['currency'])))
            item_cost.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.tbl_labor_summary.setItem(row, 5, item_cost)
            row += 1

        # add a totals row for total hours (bold)
        font_bold = QFont()
        font_bold.setBold(True)

        item_label = QTableWidgetItem(CFG.LABOR_TOTAL_HOURS_LABEL)
        item_label.setFlags(item_label.flags() & ~Qt.ItemIsSelectable)
        item_label.setFont(font_bold)
        self.tbl_labor_summary.setItem(row, 0, item_label)
        item_total_hours = QTableWidgetItem(f"{total_hours:.2f}")
        item_total_hours.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
        item_total_hours.setFont(font_bold)
        self.tbl_labor_summary.setItem(row, 2, item_total_hours)
        row += 1

        # add per-currency totals (bold)
        for cur, amt in totals_by_currency.items():
            label = QTableWidgetItem(f"Total ({cur})")
            label.setFlags(label.flags() & ~Qt.ItemIsSelectable)
            label.setFont(font_bold)
            self.tbl_labor_summary.setItem(row, 0, label)
            val = QTableWidgetItem(fmt_currency(amt, currency_symbol_from_code(cur)))
            val.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            val.setFont(font_bold)
            self.tbl_labor_summary.setItem(row, 5, val)
            row += 1

        # adjust row sizes to fit content and ensure columns keep stretching to fill available space
        self.tbl_labor_summary.resizeRowsToContents()
        # Avoid calling resizeColumnsToContents() which may shrink the table to the content width
        from PySide6.QtWidgets import QHeaderView
        self.tbl_labor_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # compute a tight fixed height so the table does not leave an empty gap after the last row
        content_height = self.tbl_labor_summary.horizontalHeader().height()
        for i in range(self.tbl_labor_summary.rowCount()):
            content_height += self.tbl_labor_summary.rowHeight(i)
        # add small padding
        content_height += 6
        # set the fixed height so the table fits exactly the rows (but allow it to grow if many rows)
        max_h = 300
        h = min(content_height, max_h)
        self.tbl_labor_summary.setFixedHeight(h)
        # ensure geometry is updated so layout allocates correct width
        self.tbl_labor_summary.updateGeometry()

        self.lbl_labor_note.setText(note)
    
    def show_labor_details(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Labor details", "Please select a project.")
            return
        dlg = ResourceLaborDialog(self, project_id=pid, reporting_service=self._reporting_service, task_service=self._task_service, resource_service=self._resource_service)
        dlg.exec()
        # After the details dialog closes, refresh the labor summary in the cost tab
        self.reload_costs()

    # ---------------- Actions ---------------- #

    def create_cost_item(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "New cost item", "Please select a project.")
            return

        dlg = CostEditDialog(
            self,
            project=self._current_project,
            tasks=self._project_tasks,
            cost_item=None,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._cost_service.add_cost_item(
                    project_id=pid,
                    description=dlg.description,
                    task_id=dlg.task_id,
                    planned_amount=dlg.planned_amount,
                    committed_amount=dlg.committed_amount,
                    actual_amount=dlg.actual_amount,
                    cost_type=dlg.cost_type,
                    incurred_date=dlg.incurred_date_value,
                    currency_code=dlg.currency_code,
                )
            except ValidationError as e:
                QMessageBox.warning(self, "Validation error", str(e))
                continue
            except NotFoundError as e:
                QMessageBox.warning(self, "Error", str(e))
                continue

            self.reload_costs()
            return

    def edit_cost_item(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Edit cost item", "Please select a project.")
            return
        item = self._get_selected_cost()
        if not item:
            QMessageBox.information(self, "Edit cost item", "Please select a cost item.")
            return

        dlg = CostEditDialog(
            self,
            project=self._current_project,
            tasks=self._project_tasks,
            cost_item=item,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                # update planned & actual via service
                self._cost_service.update_cost_item(
                    cost_id=item.id,
                    actual_amount=dlg.actual_amount,
                    description=dlg.description,
                    planned_amount=dlg.planned_amount,
                    committed_amount=dlg.committed_amount,
                    cost_type=dlg.cost_type,
                    incurred_date=dlg.incurred_date_value,
                    currency_code=dlg.currency_code,
                )
                # (if service signature differs, split into two calls)
            except (ValidationError, NotFoundError) as e:
                QMessageBox.warning(self, "Error", str(e))
                continue
            self.reload_costs()
            return

    def delete_cost_item(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Delete cost item", "Please select a project.")
            return
        item = self._get_selected_cost()
        if not item:
            QMessageBox.information(self, "Delete cost item", "Please select a cost item.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm delete",
            f"Delete cost item '{item.description}'?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._cost_service.delete_cost_item(item.id)
        except NotFoundError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        self.reload_costs()

    def _on_labor_table_selected(self):
        # Clear selection in cost table when labor table is interacted with
        if self.table.selectionModel():
            self.table.clearSelection()
      



