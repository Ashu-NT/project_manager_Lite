from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QHeaderView, QLabel, QMessageBox, QTableView, QTableWidget, QTableWidgetItem

from core.models import CostType
from core.models import Project
from core.services.cost import CostService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.cost.labor_dialogs import ResourceLaborDialog
from ui.styles.formatting import currency_symbol_from_code, fmt_currency
from ui.styles.ui_config import UIConfig as CFG


class CostLaborSummaryMixin:
    _reporting_service: ReportingService
    _cost_service: CostService
    _task_service: TaskService
    _resource_service: ResourceService
    _current_project: Project | None
    tbl_labor_summary: QTableWidget
    lbl_labor_note: QLabel
    table: QTableView

    def reload_labor_summary(self, project_id: str):
        details = self._reporting_service.get_project_labor_details(project_id)
        self.tbl_labor_summary.setRowCount(0)
        if not details:
            self.tbl_labor_summary.setRowCount(1)
            self.tbl_labor_summary.setItem(0, 0, QTableWidgetItem(CFG.NO_LABOR_ASSIGNMENTS_TEXT))
            for c in range(1, self.tbl_labor_summary.columnCount()):
                self.tbl_labor_summary.setItem(0, c, QTableWidgetItem(""))
            self.lbl_labor_note.setText("")
            return

        rows_data = []
        totals_by_currency: dict[str, float] = {}
        total_hours = 0.0
        for r in details:
            for a in r.assignments:
                rows_data.append(
                    {
                        "resource_name": r.resource_name,
                        "task_name": a.task_name,
                        "hours": float(a.hours or 0.0),
                        "hourly_rate": float(a.hourly_rate or 0.0),
                        "currency": (
                            a.currency_code
                            or (
                                r.currency_code
                                or (self._current_project.currency if self._current_project else "")
                            )
                            or ""
                        ).upper(),
                        "cost": float(a.cost or 0.0),
                    }
                )
                total_hours += float(a.hours or 0.0)
                cur = (
                    a.currency_code
                    or (r.currency_code or (self._current_project.currency if self._current_project else ""))
                    or ""
                ).upper()
                totals_by_currency[cur] = totals_by_currency.get(cur, 0.0) + float(a.cost or 0.0)

        try:
            costs = self._cost_service.list_cost_items_for_project(project_id)
            manual_labor_exists = any(getattr(c, "cost_type", None) == CostType.LABOR for c in costs)
        except Exception:
            manual_labor_exists = False

        note = (
            CFG.LABOR_IGNORED_NOTE
            if (manual_labor_exists and any(amt > 0 for amt in totals_by_currency.values()))
            else ""
        )

        base_rows = len(rows_data)
        total_rows = base_rows + 1 + len(totals_by_currency)
        self.tbl_labor_summary.setRowCount(total_rows)

        from PySide6.QtCore import Qt as _Qt

        row = 0
        for rdata in rows_data:
            self.tbl_labor_summary.setItem(row, 0, QTableWidgetItem(rdata["resource_name"]))
            self.tbl_labor_summary.setItem(row, 1, QTableWidgetItem(rdata["task_name"]))
            item_h = QTableWidgetItem(f"{rdata['hours']:.2f}")
            item_h.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.tbl_labor_summary.setItem(row, 2, item_h)
            item_rate = QTableWidgetItem(
                fmt_currency(rdata["hourly_rate"], currency_symbol_from_code(rdata["currency"]))
            )
            item_rate.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.tbl_labor_summary.setItem(row, 3, item_rate)
            self.tbl_labor_summary.setItem(row, 4, QTableWidgetItem(rdata["currency"] or ""))
            item_cost = QTableWidgetItem(
                fmt_currency(rdata["cost"], currency_symbol_from_code(rdata["currency"]))
            )
            item_cost.setTextAlignment(_Qt.AlignRight | _Qt.AlignVCenter)
            self.tbl_labor_summary.setItem(row, 5, item_cost)
            row += 1

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

        self.tbl_labor_summary.resizeRowsToContents()
        self.tbl_labor_summary.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        content_height = self.tbl_labor_summary.horizontalHeader().height()
        for i in range(self.tbl_labor_summary.rowCount()):
            content_height += self.tbl_labor_summary.rowHeight(i)
        content_height += 6
        max_h = 300
        h = min(content_height, max_h)
        self.tbl_labor_summary.setFixedHeight(h)
        self.tbl_labor_summary.updateGeometry()

        self.lbl_labor_note.setText(note)

    def show_labor_details(self):
        pid = self._current_project_id()
        if not pid:
            QMessageBox.information(self, "Labor details", "Please select a project.")
            return
        dlg = ResourceLaborDialog(
            self,
            project_id=pid,
            reporting_service=self._reporting_service,
            task_service=self._task_service,
            resource_service=self._resource_service,
        )
        dlg.exec()
        self.reload_costs()

    def _on_labor_table_selected(self):
        if self.table.selectionModel():
            self.table.clearSelection()
