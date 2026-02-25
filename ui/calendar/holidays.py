from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDateEdit, QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem

from core.exceptions import BusinessRuleError, ValidationError
from core.services.work_calendar import WorkCalendarService


class CalendarHolidaysMixin:
    _wc_service: WorkCalendarService
    holiday_table: QTableWidget
    holiday_date_edit: QDateEdit
    holiday_name_edit: QLineEdit

    def load_holidays(self):
        holidays = self._wc_service.list_holidays()
        self.holiday_table.setRowCount(0)
        for h in holidays:
            row = self.holiday_table.rowCount()
            self.holiday_table.insertRow(row)
            item_date = QTableWidgetItem(h.date.isoformat())
            item_name = QTableWidgetItem(h.name or "")
            item_date.setData(Qt.UserRole, h.id)
            self.holiday_table.setItem(row, 0, item_date)
            self.holiday_table.setItem(row, 1, item_name)

    def add_holiday(self):
        qd = self.holiday_date_edit.date()
        if not qd.isValid():
            QMessageBox.warning(self, "Holiday", "Please choose a valid date.")
            return
        d = date(qd.year(), qd.month(), qd.day())
        name = self.holiday_name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Holiday", "Please enter a name for the non-working day.")
            return

        try:
            self._wc_service.add_holiday(d, name)
        except (ValidationError, BusinessRuleError) as e:
            QMessageBox.warning(self, "Validation error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Holiday", str(e))
            return

        self.holiday_name_edit.clear()
        self.load_holidays()

    def delete_selected_holiday(self):
        row = self.holiday_table.currentRow()
        if row < 0:
            return
        item = self.holiday_table.item(row, 0)
        if not item:
            return
        hol_id = item.data(Qt.UserRole)
        if not hol_id:
            return

        confirm = QMessageBox.question(
            self,
            "Delete non-working day",
            "Remove the selected non-working day from the calendar?",
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            self._wc_service.delete_holiday(hol_id)
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.load_holidays()
