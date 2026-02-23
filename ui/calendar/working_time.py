from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QLabel, QMessageBox, QSpinBox

from core.exceptions import ValidationError
from core.services.work_calendar import WorkCalendarEngine, WorkCalendarService


class CalendarWorkingTimeMixin:
    _wc_engine: WorkCalendarEngine
    _wc_service: WorkCalendarService
    day_checks: list[QCheckBox]
    hours_spin: QSpinBox
    summary_label: QLabel

    def load_calendar_config(self):
        cal = self._wc_engine._get_calendar()
        if cal:
            working_days = set(cal.working_days or [])
            for cb in self.day_checks:
                cb.setChecked(cb.day_index in working_days)
            if cal.hours_per_day:
                self.hours_spin.setValue(int(cal.hours_per_day))

            self._update_summary_label(working_days, cal.hours_per_day or 8.0)
        else:
            self._update_summary_label({0, 1, 2, 3, 4}, 8.0)

    def _update_summary_label(self, working_days: set[int], hours_per_day: float):
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        active_names = [day_names[i] for i in sorted(working_days)]
        self.summary_label.setText(
            "This calendar controls all schedule calculations.\n"
            f"Currently: {', '.join(active_names) or 'no days'} are working days, "
            f"{hours_per_day:g} hours per day."
        )

    def save_calendar(self):
        working_days = {cb.day_index for cb in self.day_checks if cb.isChecked()}
        hours = float(self.hours_spin.value())
        try:
            cal = self._wc_service.set_working_days(working_days, hours_per_day=hours)
        except ValidationError as e:
            QMessageBox.warning(self, "Validation error", str(e))
            return

        self._update_summary_label(set(cal.working_days or []), cal.hours_per_day or hours)
        QMessageBox.information(
            self,
            "Calendar saved",
            "Working calendar has been saved.\n\n"
            "Tip: Recalculate project schedules so tasks use these updated working days "
            "and non-working dates.",
        )
