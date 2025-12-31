# ui/cost_tab.py
from __future__ import annotations
from typing import Optional
from datetime import date

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex,QDate
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QPushButton,
    QTableView, QTableWidget, QTableWidgetItem, QDialog, QFormLayout, QTextEdit, QDoubleSpinBox,
    QDialogButtonBox, QMessageBox, QDateEdit, QGroupBox, QListWidget, QListWidgetItem, QInputDialog
)

from core.services.project_service import ProjectService
from core.services.task_service import TaskService
from core.services.cost_service import CostService
from core.services.reporting_service import ReportingService, LaborResourceRow
from core.services.resource_service import ResourceService
from core.exceptions import ValidationError, NotFoundError
from core.models import Project, Task, CostItem  , CostType, Resource

from ui.styles.formatting import fmt_currency, currency_symbol_from_code
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG, CurrencyType


class CostTableModel(QAbstractTableModel):
    HEADERS = ["Description", "Task","Type", "Planned", "Committed", "Actual", "Incurred Date"]

    def __init__(self, costs: list[CostItem] | None = None, parent=None):
        super().__init__(parent)
        self._costs: list[CostItem] = costs or []
        # cache of task_id -> task_name to show nicer labels
        self._task_names: dict[str, str] = {}
        self._project_currency = ""
        self._tasks_by_id: dict[str, Task] = {}
        
    def set_context(self, tasks_by_id:dict, project_currency: str=""):
        self._tasks_by_id = tasks_by_id or {}
        self._project_currency = (project_currency or "").strip().upper()
        self.layoutChanged.emit()

    def set_costs(self, costs: list[CostItem], task_names: dict[str, str]):
        self.beginResetModel()
        self._costs = costs
        self._task_names = task_names
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self._costs)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.EditRole):
            return None
        c = self._costs[index.row()]
        col = index.column()
        if col == 0:
            return c.description
        elif col == 1:
            if c.task_id and c.task_id in self._task_names:
                return self._task_names[c.task_id]
            return ""
        elif col == 2:
            return c.cost_type.value if hasattr(c.cost_type, "value") else str(c.cost_type)
        elif col == 3:
            return fmt_currency(c.planned_amount, currency_symbol_from_code(c.currency_code or self._project_currency))
        elif col == 4:
            return fmt_currency(c.committed_amount, currency_symbol_from_code(c.currency_code or self._project_currency))
        elif col == 5:
            return fmt_currency(c.actual_amount, currency_symbol_from_code(c.currency_code or self._project_currency))
        elif col == 6:
            return c.incurred_date.isoformat() if c.incurred_date else ""
        return None

    def headerData(self, section: int, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def get_cost(self, row: int) -> Optional[CostItem]:
        if 0 <= row < len(self._costs):
            return self._costs[row]
        return None
    
class CostEditDialog(QDialog):
    def __init__(
        self,
        parent=None,
        project: Project | None = None,
        tasks: list[Task] | None = None,
        cost_item: CostItem | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Cost item" + (" - Edit" if cost_item else " - New"))
        self._project = project
        self._tasks = tasks or []
        self._cost_item = cost_item

        self.desc_edit = QTextEdit()
        self.desc_edit.setSizePolicy(CFG.TEXTEDIT_POLICY)
        self.desc_edit.setMinimumHeight(CFG.TEXTEDIT_MIN_HEIGHT)

        self.planned_spin = QDoubleSpinBox()
        self.actual_spin = QDoubleSpinBox()
        self.committed_spin = QDoubleSpinBox()
        
        for spin in (self.planned_spin, self.actual_spin, self.committed_spin):
            spin.setSizePolicy(CFG.INPUT_POLICY)
            spin.setFixedHeight(CFG.INPUT_HEIGHT)
            spin.setDecimals(CFG.MONEY_DECIMALS)
            spin.setSingleStep(CFG.MONEY_STEP)
            spin.setMinimum(CFG.MONEY_MIN)
            spin.setMaximum(CFG.MONEY_MAX)
            spin.setAlignment(CFG.ALIGN_RIGHT)
        
        self.task_combo = QComboBox()
        self.type_combo = QComboBox()
        for combo in (self.task_combo, self.type_combo):
            combo.setSizePolicy(CFG.INPUT_POLICY)
            combo.setFixedHeight(CFG.INPUT_HEIGHT)
            combo.setEditable(CFG.COMBO_EDITABLE)
            combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)
        
        self.currency_combo = QComboBox()
        self.currency_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.currency_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.currency_combo.setEditable(CFG.COMBO_EDITABLE)
        self.currency_combo.setMaxVisibleItems(CFG.COMBO_MAX_VISIBLE)
        
        self.incurred_date = QDateEdit()
        self.incurred_date.setSizePolicy(CFG.INPUT_POLICY)
        self.incurred_date.setFixedHeight(CFG.INPUT_HEIGHT)
        
        self.incurred_date.setDate(QDate.currentDate())
        self.incurred_date.setCalendarPopup(True)
        self.incurred_date.setDisplayFormat(CFG.DATE_FORMAT)
        
        for cur in CurrencyType:
            self.currency_combo.addItem(cur.value)
        
        # Task combo: first option is no-task
        self.task_combo.addItem("(none)", userData=None)
        
        for ct in CostType:
            if ct == CostType.LABOR:
                continue  # skip LABOR type in manual cost item editing
            self.type_combo.addItem(ct.value, userData=ct)
        
        for t in self._tasks:
            self.task_combo.addItem(t.name, userData=t.id)

        if cost_item:
            self.desc_edit.setPlainText(cost_item.description or "")
            if cost_item.planned_amount is not None:
                self.planned_spin.setValue(cost_item.planned_amount)
            if cost_item.actual_amount is not None:
                self.actual_spin.setValue(cost_item.actual_amount)
            # select task
            if cost_item.task_id:
                for i in range(1, self.task_combo.count()):
                    if self.task_combo.itemData(i) == cost_item.task_id:
                        self.task_combo.setCurrentIndex(i)
                        break
            # select cost type
            if cost_item.cost_type is not None:
                for i in range(self.type_combo.count()):
                    if self.type_combo.itemData(i) == cost_item.cost_type:
                        self.type_combo.setCurrentIndex(i)
                        break

        form = QFormLayout()
        
        form.setLabelAlignment(CFG.ALIGN_RIGHT | CFG.ALIGN_CENTER)
        form.setFormAlignment(CFG.ALIGN_TOP)
        form.setHorizontalSpacing(CFG.SPACING_MD)
        form.setVerticalSpacing(CFG.SPACING_SM)
        
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.DontWrapRows)
        
        form.addRow("Task:", self.task_combo)
        form.addRow("Planned amount:", self.planned_spin)
        form.addRow("Actual amount:", self.actual_spin)
        form.addRow("Committed Amount:", self.committed_spin)
        form.addRow("Type:", self.type_combo)
        form.addRow("Incurred date:", self.incurred_date)
        form.addRow("Currency (Optional):", self.currency_combo)
        form.addRow("Description:", self.desc_edit)
        

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.setCenterButtons(True)

        layout = QVBoxLayout(self)
        
        layout.setSpacing(CFG.SPACING_LG)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        layout.addLayout(form)
        layout.addWidget(buttons)

    @property
    def description(self) -> str:
         return self.desc_edit.toPlainText().strip()

    @property
    def task_id(self) -> Optional[str]:
        idx = self.task_combo.currentIndex()
        if idx < 0:
            return None
        return self.task_combo.itemData(idx)

    @property
    def planned_amount(self) -> float:
        return self.planned_spin.value()

    @property
    def actual_amount(self) -> Optional[float]:
        val = self.actual_spin.value()
        # treat 0 as 0, not None (depends on your preference)
        return val
    
    @property
    def cost_type(self) -> CostType:
        idx =  self.type_combo.currentIndex()
        return self.type_combo.itemData(idx) or CostType.OVERHEAD
    
    @property
    def committed_amount(self) -> float:
        return self.committed_spin.value()
    
    @property
    def incurred_date_value(self) -> date | None:
        if not self.incurred_date.date().isValid():
            return None
        qd = self.incurred_date.date()
        return date(qd.year(), qd.month(),qd.day())
    
    @property
    def currency_code(self) -> str | None:
        code = self.currency_combo.currentText().strip()
        return code or None
    
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
                lines.append("Planned Total exceeds budget.")
            else:
                lines.append(f"Total Planned Cost: {fmt_currency(planed_total, sym)}")
                lines.append(f"Total Actual Cost: {fmt_currency(actual_total, sym)}")
                lines.append("Note: Set project budget to track remainding budget")
                
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
                True
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
                # then set actual amount if > 0
                # (depends on your service API; here's one approach)
                costs = self._cost_service.list_cost_items_for_project(pid)
                new_item = costs[-1] if costs else None
                if new_item and dlg.actual_amount is not None:
                    self._cost_service.update_cost_item(
                        cost_id=new_item.id,
                        actual_amount=dlg.actual_amount,
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
      


class ResourceLaborDialog(QDialog):
    def __init__(self, parent, project_id: str, reporting_service: ReportingService, task_service: TaskService, resource_service: ResourceService):
        super().__init__(parent)
        self.setWindowTitle("Labor cost details")
        self._project_id = project_id
        self._reporting_service = reporting_service
        self._task_service = task_service
        self._resource_service = resource_service

        self.table = QTableView()
        self._model = None

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
        # plan vs actual rows
        rows = self._reporting_service.get_project_labor_plan_vs_actual(self._project_id)

        resource_count = len(rows)
        total_planned_cost = 0.0
        total_actual_cost = 0.0
        total_actual_hours = 0.0

        totals_by_currency_planned: dict[str, float] = {}
        totals_by_currency_actual: dict[str, float] = {}

        for r in rows:
            cur_p = (r.planned_currency_code or "").upper() or "—"
            cur_a = (r.actual_currency_code or "").upper() or cur_p or "—"
            totals_by_currency_planned[cur_p] = totals_by_currency_planned.get(cur_p, 0.0) + float(r.planned_cost or 0.0)
            totals_by_currency_actual[cur_a] = totals_by_currency_actual.get(cur_a, 0.0) + float(r.actual_cost or 0.0)

            total_planned_cost += float(r.planned_cost or 0.0)
            total_actual_cost += float(r.actual_cost or 0.0)
            total_actual_hours += float(r.actual_hours or 0.0)

        # overview string (shows totals per currency)
        def _fmt_totals(totals: dict[str, float]) -> str:
            parts = []
            for cur, amt in totals.items():
                sym = currency_symbol_from_code(cur)
                parts.append(fmt_currency(amt, sym) if sym else f"{cur} {fmt_currency(amt, '')}".strip())
            return "; ".join(parts)

        self.lbl_overview.setText(
            f"{resource_count} resources • Actual: {total_actual_hours:.2f} hrs • "
            f"Planned totals: {_fmt_totals(totals_by_currency_planned)} • "
            f"Actual totals: {_fmt_totals(totals_by_currency_actual)}"
        )

        # explanatory note about ignoring manual LABOR cost items when computed labor exists
        note = ""
        try:
            if isinstance(self.parent(), CostTab):
                costs = self.parent()._cost_service.list_cost_items_for_project(self._project_id)
                manual_labor_exists = any(getattr(c, 'cost_type', None) == CostType.LABOR for c in costs)
                if manual_labor_exists and total_actual_cost > 0:
                    note = CFG.LABOR_IGNORED_NOTE
        except Exception:
            note = ""
        self.lbl_note.setText(note)

        # Table model: Plan vs Actual per resource
        class _M(QAbstractTableModel):
            HEADERS = ["Resource", "Planned Hours", "Planned Cost", "Actual Hours", "Actual Cost", "Variance", "Currency"]

            def __init__(self, data):
                super().__init__()
                self._data = data

            def rowCount(self, parent=QModelIndex()):
                return len(self._data)

            def columnCount(self, parent=QModelIndex()):
                return len(self.HEADERS)

            def data(self, index, role=Qt.DisplayRole):
                if not index.isValid() or role != Qt.DisplayRole:
                    return None
                r = self._data[index.row()]
                col = index.column()

                cur = (r.actual_currency_code or r.planned_currency_code or "").upper()
                sym = currency_symbol_from_code(cur)

                if col == 0:
                    return r.resource_name
                elif col == 1:
                    return f"{float(r.planned_hours or 0.0):.2f}"
                elif col == 2:
                    return fmt_currency(float(r.planned_cost or 0.0), sym)
                elif col == 3:
                    return f"{float(r.actual_hours or 0.0):.2f}"
                elif col == 4:
                    return fmt_currency(float(r.actual_cost or 0.0), sym)
                elif col == 5:
                    return fmt_currency(float(r.variance_cost or 0.0), sym)
                elif col == 6:
                    return cur or ""
                return None

            def headerData(self, section, orientation, role=Qt.DisplayRole):
                if orientation == Qt.Horizontal and role == Qt.DisplayRole:
                    return self.HEADERS[section]
                return super().headerData(section, orientation, role)

            def get_row(self, row: int):
                if 0 <= row < len(self._data):
                    return self._data[row]
                return None

        self._model = _M(rows)
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
        r = self._model.get_row(row)
        if not r:
            QMessageBox.warning(self, "Assignments", "Failed to locate resource.")
            return
        # find Resource dataclass via resource_service
        resources = self._resource_service.list_resources()
        res_obj = next((x for x in resources if x.id == r.resource_id), None)
        if not res_obj:
            QMessageBox.warning(self, "Assignments", "Resource object not found.")
            return
        # Open assignments dialog
        # we only have project id; build a lightweight Project object for dialog title
        project_name = ""
        try:
            # nicer title if we can resolve project name
            p = None
            if isinstance(self.parent(), CostTab) and self.parent()._current_project:
                p = self.parent()._current_project
            project_name = p.name if p else self._project_id
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

        # Refresh parent views (read-only dialog, but keeps UI consistent)
        self.reload()
        self.reload_costs()
        
    def reload_costs(self):
        if isinstance(self.parent(), CostTab):
            self.parent().reload_costs()

class ResourceAssignmentsDialog(QDialog):
    """
    Read-only view: shows breakdown of the selected resource assignments in the project:
      - Allocation %
      - Hours logged
      - Optional cost (hours * resolved project rate)
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
        self.setWindowTitle(f"{resource.name} — assignments in {project_name}")
        self._task_service = task_service
        self._reporting_service = reporting_service
        self._project_id = project_id
        self._project_name = project_name
        self._resource = resource

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
        # Use ReportingService rows to get cost/rate/currency already resolved professionally
        labor_rows = self._reporting_service.get_project_labor_details(self._project_id)

        # Find the resource entry
        rr = next((x for x in labor_rows if x.resource_id == self._resource.id), None)
        if not rr:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No assignments found"))
            for c in range(1, self.table.columnCount()):
                self.table.setItem(0, c, QTableWidgetItem(""))
            self.lbl_totals.setText("")
            return

        # Each assignment row already contains task_name/hours/rate/cost/currency
        assigns = rr.assignments or []
        self.table.setRowCount(len(assigns))

        total_hours = 0.0
        total_cost = 0.0
        cur = (rr.currency_code or "").upper()

        from PySide6.QtCore import Qt as _Qt
        for i, a in enumerate(assigns):
            self.table.setItem(i, 0, QTableWidgetItem(a.task_name))

            # Allocation %: pull from TaskService assignment (because labor row doesn't store allocation)
            alloc = 0.0
            try:
                obj = self._task_service.get_assignment(a.assignment_id)
                alloc = float(getattr(obj, "allocation_percent", 0.0) or 0.0) if obj else 0.0
            except Exception:
                alloc = 0.0

            it_alloc = QTableWidgetItem(f"{alloc:.1f}")
            it_alloc.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.table.setItem(i, 1, it_alloc)

            it_h = QTableWidgetItem(f"{float(a.hours or 0.0):.2f}")
            it_h.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.table.setItem(i, 2, it_h)

            sym = currency_symbol_from_code(a.currency_code or cur)
            it_cost = QTableWidgetItem(fmt_currency(float(a.cost or 0.0), sym))
            it_cost.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.table.setItem(i, 3, it_cost)

            total_hours += float(a.hours or 0.0)
            total_cost += float(a.cost or 0.0)
            if not cur and a.currency_code:
                cur = (a.currency_code or "").upper()

        sym = currency_symbol_from_code(cur)
        self.lbl_totals.setText(
            f"Total hours: {total_hours:.2f} hrs • Total cost: {fmt_currency(total_cost, sym)}"
        )

        self.table.resizeRowsToContents()

              