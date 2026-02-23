from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QMessageBox

from core.exceptions import ValidationError


class CalendarCalculatorMixin:
    def run_calendar_calc(self):
        qd = self.calc_start.date()
        if not qd.isValid():
            QMessageBox.warning(self, "Calculator", "Invalid start date.")
            return
        start = date(qd.year(), qd.month(), qd.day())
        n = self.calc_days_spin.value()
        if n <= 0:
            QMessageBox.warning(
                self,
                "Calculator",
                "Please enter a positive number of working days (1 or more).",
            )
            return

        try:
            result = self._wc_engine.add_working_days(start, n)
        except ValidationError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        skipped_non_working = 0
        current = start
        while current <= result:
            if not self._wc_engine.is_working_day(current):
                skipped_non_working += 1
            current = current.fromordinal(current.toordinal() + 1)

        self.calc_result_label.setText(
            f"Result: Start {start.isoformat()} + {n} working days = {result.isoformat()}\n"
            f"(Skipped {skipped_non_working} non-working days "
            f"based on your working week and holidays.)"
        )
