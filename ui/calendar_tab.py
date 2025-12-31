# ui/calendar_tab.py
from __future__ import annotations
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QGroupBox, QSpinBox, QDateEdit, QLineEdit,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QComboBox
)
from PySide6.QtCore import QDate

from core.services.work_calendar_service import WorkCalendarService
from core.services.work_calendar_engine import WorkCalendarEngine
from core.services.scheduling_service import SchedulingEngine
from core.services.project_service import ProjectService
from core.services.task_service import TaskService
from core.exceptions import ValidationError, BusinessRuleError
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from core.events.domain_events import domain_events

class CalendarTab(QWidget):
    """
    User-friendly calendar configuration:

    - Working days + hours per day
    - Non-working days (holidays/shutdowns)
    - Working-day calculator (what does "5 working days" really mean?)
    - Recalculate project schedule using current calendar
    """

    def __init__(
        self,
        work_calendar_service: WorkCalendarService,
        work_calendar_engine: WorkCalendarEngine,
        scheduling_engine: SchedulingEngine,
        project_service: ProjectService,
        task_service: TaskService,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._wc_service = work_calendar_service
        self._wc_engine = work_calendar_engine
        self._scheduling_engine = scheduling_engine
        self._project_service = project_service
        self._task_service = task_service

        self._setup_ui()
        self.load_calendar_config()
        self.load_holidays()
        self.reload_projects()
        domain_events.project_changed.connect(self._on_project_changed)
    # ------------------------------------------------------------------ #
    # UI setup
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_SM)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )
        self.setMinimumSize(self.sizeHint())

        # ---- Working time group ---- #
        grp_days = QGroupBox("Working time (used for all schedule calculations)")
        grp_days.setFont(CFG.GROUPBOX_TITLE_FONT)
        days_layout = QVBoxLayout(grp_days)
        days_layout.setSpacing(CFG.SPACING_SM)

        self.summary_label = QLabel(
            "This calendar controls how task durations and dependencies are "
            "converted into real dates.\n"
            "Working days are counted for CPM, Gantt, and all scheduling."
        )
        self.summary_label.setWordWrap(True)
        days_layout.addWidget(self.summary_label)

        days_row = QHBoxLayout()
    
        self.day_checks = []
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, name in enumerate(day_names):
            cb = QCheckBox(name)
            cb.setChecked(i < 5)  # default Mon-Fri
            cb.day_index = i
            cb.setToolTip("Include %s as a working day (tasks can be scheduled here)." % name)
            self.day_checks.append(cb)
            days_row.addWidget(cb)
        days_row.addStretch()
        days_layout.addLayout(days_row)

        hours_row = QHBoxLayout()
        hours_row.addWidget(QLabel("Working hours per day:"))
        self.hours_spin = QSpinBox()
        self.hours_spin.setMinimum(CFG.MIN_WORKING_HOURS)
        self.hours_spin.setMaximum(CFG.MAX_WORKING_HOURS)
        self.hours_spin.setValue(CFG.WORKING_HOURS_IN_DAY)
        self.hours_spin.setToolTip(
            "Used for reporting on capacity/cost. "
            "Scheduling itself uses working DAYS, but this defines how long a day is."
        )
        hours_row.addWidget(self.hours_spin)

        self.btn_save_calendar = QPushButton(CFG.APPLY_WORKING_TIME_LABEL)
        self.btn_save_calendar.setToolTip(
            "Save these working days and hours and use them for all future schedule calculations."
        )
        hours_row.addWidget(self.btn_save_calendar)
        hours_row.addStretch()
        days_layout.addLayout(hours_row)

        layout.addWidget(grp_days)

        # ---- Holidays group ---- #
        grp_holidays = QGroupBox("Non-working days (holidays, shutdowns, special days)")
        grp_holidays.setFont(CFG.GROUPBOX_TITLE_FONT)
        
        hol_layout = QVBoxLayout(grp_holidays)
        hol_layout.setSpacing(CFG.SPACING_SM)

        desc = QLabel(
            "Tasks will NEVER be scheduled on these dates, even if they fall on a working weekday.\n"
            "Use this for public holidays, company shutdowns, or any special non-working days."
        )
        desc.setWordWrap(True)
        hol_layout.addWidget(desc)

        self.holiday_table = QTableWidget(0, 2)
        self.holiday_table.setHorizontalHeaderLabels(CFG.HOLIDAY_TABLE_HEADERS)
        self.holiday_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.holiday_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.holiday_table.setToolTip(
            "List of specific dates that are treated as non-working days in all schedules."
        )
        style_table(self.holiday_table)
        hol_layout.addWidget(self.holiday_table)

        row = QHBoxLayout()
        self.holiday_date_edit = QDateEdit()
        self.holiday_date_edit.setDisplayFormat(CFG.DATE_FORMAT)
        self.holiday_date_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        self.holiday_date_edit.setSizePolicy(CFG.INPUT_POLICY)
        self.holiday_date_edit.setCalendarPopup(True)
        self.holiday_date_edit.setDate(QDate.currentDate())
        self.holiday_date_edit.setToolTip("Pick a date that should be treated as non-working.")

        self.holiday_name_edit = QLineEdit()
        self.holiday_name_edit.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        self.holiday_name_edit.setSizePolicy(CFG.INPUT_POLICY)
        
        self.holiday_name_edit.setPlaceholderText("e.g. Christmas, National Holiday, Plant Shutdown")
        self.holiday_name_edit.setToolTip("Short description of this non-working day.")

        self.btn_add_holiday = QPushButton(CFG.ADD_NON_WORKING_DAY_LABEL)
        self.btn_add_holiday.setToolTip("Add the selected date and name as a non-working day.")
        self.btn_delete_holiday = QPushButton(CFG.REMOVE_SELECTED_LABEL)
        self.btn_delete_holiday.setToolTip("Remove the currently selected non-working day from the calendar.")
        
        for btn in [self.btn_add_holiday, self.btn_delete_holiday]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)

        row.addWidget(QLabel("Date:"))
        row.addWidget(self.holiday_date_edit)
        row.addWidget(QLabel("Name:"))
        row.addWidget(self.holiday_name_edit)
        row.addWidget(self.btn_add_holiday)
        row.addWidget(self.btn_delete_holiday)
        row.addStretch()
        hol_layout.addLayout(row)

        layout.addWidget(grp_holidays)

        # ---- Calculator group ---- #
        grp_calc = QGroupBox("Working-day calculator")
        grp_calc.setFont(CFG.GROUPBOX_TITLE_FONT)
        
        calc_layout = QVBoxLayout(grp_calc)
        calc_layout.setSpacing(CFG.SPACING_SM)
        
        calc_desc = QLabel(
            "Use this tool to see how the current calendar interprets a duration in working days.\n"
            "This is exactly how task durations are converted into dates in CPM and Gantt."
        )
        calc_desc.setWordWrap(True)
        calc_layout.addWidget(calc_desc)

        calc_row = QHBoxLayout()
        self.calc_start = QDateEdit()
        self.calc_start.setCalendarPopup(True)
        self.calc_start.setDisplayFormat(CFG.DATE_FORMAT)
        self.calc_start.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        self.calc_start.setSizePolicy(CFG.INPUT_POLICY)
        self.calc_start.setDate(QDate.currentDate())
        self.calc_start.setToolTip("Starting date for the calculation (e.g. task start).")

        self.calc_days_spin = QSpinBox()
        self.calc_days_spin.setMinimumWidth(CFG.INPUT_MIN_WIDTH)
        self.calc_days_spin.setSizePolicy(CFG.INPUT_POLICY)
        self.calc_days_spin.setMinimum(1)  # engine supports only positive
        self.calc_days_spin.setMaximum(3650)
        self.calc_days_spin.setValue(5)
        self.calc_days_spin.setToolTip(
            "How many WORKING days to add. Weekends and non-working days will be skipped."
        )

        self.btn_calc = QPushButton(CFG.CALCULATE_LABEL)
        self.btn_calc.setMinimumHeight(CFG.BUTTON_HEIGHT)
        self.btn_calc.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_calc.setToolTip(
            "Compute: Start date + N working days = end date, using the current calendar."
        )
        self.calc_result_label = QLabel("Result: (not calculated yet)")
        self.calc_result_label.setWordWrap(True)

        calc_row.addWidget(QLabel("Start date:"))
        calc_row.addWidget(self.calc_start)
        calc_row.addWidget(QLabel("Duration (working days):"))
        calc_row.addWidget(self.calc_days_spin)
        calc_row.addWidget(self.btn_calc)
        calc_row.addStretch()
        calc_layout.addLayout(calc_row)
        calc_layout.addWidget(self.calc_result_label)

        layout.addWidget(grp_calc)

        # ---- Project schedule recalculation ---- #
        grp_sched = QGroupBox("Recalculate project schedules with this calendar")
        grp_sched.setFont(CFG.GROUPBOX_TITLE_FONT)
        
        sched_layout = QHBoxLayout(grp_sched)
        sched_layout.setSpacing(CFG.SPACING_SM)
        
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(CFG.COMBO_MIN_WIDTH_MD)
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        
        self.project_combo.setToolTip("Pick a project whose task dates you want to recalculate.")
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        self.btn_reload_projects.setToolTip("Reload the list of projects.")
        self.btn_recalc_project = QPushButton(CFG.RECALCULATE_SCHEDULE_LABEL)
        for btn in [self.btn_reload_projects, self.btn_recalc_project]:
            btn.setMinimumHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            
        self.btn_recalc_project.setToolTip(
            "Recompute all task dates for the selected project using the current calendar."
        )

        sched_layout.addWidget(QLabel("Project:"))
        sched_layout.addWidget(self.project_combo)
        sched_layout.addWidget(self.btn_reload_projects)
        sched_layout.addWidget(self.btn_recalc_project)
        sched_layout.addStretch()
        layout.addWidget(grp_sched)

        layout.addStretch()

        # ---- Signals ---- #
        self.btn_save_calendar.clicked.connect(self.save_calendar)
        self.btn_add_holiday.clicked.connect(self.add_holiday)
        self.btn_delete_holiday.clicked.connect(self.delete_selected_holiday)
        self.btn_calc.clicked.connect(self.run_calendar_calc)
        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_recalc_project.clicked.connect(self.recalc_project_schedule)

    def _on_project_changed(self, project_id: str):
    
        projects = self._project_service.list_projects()
        # Reload project combo box
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)
        self.project_combo.blockSignals(False)
   
        # Select first project by default if current no longer valid
        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
       
        self.reload_projects()      


    # ------------------------------------------------------------------ #
    # Working time
    # ------------------------------------------------------------------ #

    def load_calendar_config(self):
        cal = self._wc_engine._get_calendar()  # or get_or_create_calendar()
        if cal:
            working_days = set(cal.working_days or [])
            for cb in self.day_checks:
                cb.setChecked(cb.day_index in working_days)
            if cal.hours_per_day:
                self.hours_spin.setValue(int(cal.hours_per_day))

            self._update_summary_label(working_days, cal.hours_per_day or 8.0)
        else:
            # default summary
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
            "and non-working dates."
        )

    # ------------------------------------------------------------------ #
    # Holidays
    # ------------------------------------------------------------------ #

    def load_holidays(self):
        holidays = self._wc_service.list_holidays()
        self.holiday_table.setRowCount(0)
        for h in holidays:
            row = self.holiday_table.rowCount()
            self.holiday_table.insertRow(row)
            item_date = QTableWidgetItem(h.date.isoformat())
            item_name = QTableWidgetItem(h.name or "")
            # store id in UserRole
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
        except ValidationError as e:
            QMessageBox.warning(self, "Validation error", str(e))
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

        self.load_holidays()

    # ------------------------------------------------------------------ #
    # Calculator
    # ------------------------------------------------------------------ #

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

        # Count skipped non-working days between start and result, just for explanation
        skipped_non_working = 0
        current = start
        while current <= result:
            if not self._wc_engine.is_working_day(current):
                skipped_non_working += 1
            current = current.fromordinal(current.toordinal() + 1)

        # Explanation text
        self.calc_result_label.setText(
            f"Result: Start {start.isoformat()} + {n} working days = {result.isoformat()}\n"
            f"(Skipped {skipped_non_working} non-working days "
            f"based on your working week and holidays.)"
        )

    # ------------------------------------------------------------------ #
    # Project schedule
    # ------------------------------------------------------------------ #

    def reload_projects(self):
        self.project_combo.clear()
        projects = self._project_service.list_projects()
        for p in projects:
            self.project_combo.addItem(p.name, userData=p.id)

    def recalc_project_schedule(self):
        idx = self.project_combo.currentIndex()
        if idx < 0:
            QMessageBox.information(self, "Schedule", "Please select a project.")
            return
        pid = self.project_combo.itemData(idx)
        name = self.project_combo.currentText()
        try:
            schedule = self._scheduling_engine.recalculate_project_schedule(pid)
        except BusinessRuleError as e:
            QMessageBox.warning(self, "Error", str(e))
            return

        QMessageBox.information(
            self,
            "Schedule recalculated",
            f"Schedule recalculated for project '{name}'.\n"
            f"Tasks updated: {len(schedule)}.\n\n"
            "Tip: Open the Tasks or Reports tab to see the updated dates and Gantt.",
        )