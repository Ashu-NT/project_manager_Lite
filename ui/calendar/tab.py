from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from core.events.domain_events import domain_events
from core.services.project import ProjectService
from core.services.scheduling import SchedulingEngine
from core.services.task import TaskService
from core.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from ui.calendar.calculator import CalendarCalculatorMixin
from ui.calendar.holidays import CalendarHolidaysMixin
from ui.calendar.project_ops import CalendarProjectOpsMixin
from ui.calendar.working_time import CalendarWorkingTimeMixin
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class CalendarTab(
    CalendarWorkingTimeMixin,
    CalendarHolidaysMixin,
    CalendarCalculatorMixin,
    CalendarProjectOpsMixin,
    QWidget,
):
    """
    Calendar tab coordinator:
    - builds widgets
    - delegates working-time/holiday/calculation/project actions to mixins
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
        self._wc_service: WorkCalendarService = work_calendar_service
        self._wc_engine: WorkCalendarEngine = work_calendar_engine
        self._scheduling_engine: SchedulingEngine = scheduling_engine
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service

        self._setup_ui()
        self.load_calendar_config()
        self.load_holidays()
        self.reload_projects()
        domain_events.project_changed.connect(self._on_project_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_SM)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)
        self.setMinimumSize(self.sizeHint())

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
            cb.setChecked(i < 5)
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
        self.holiday_name_edit.setPlaceholderText(
            "e.g. Christmas, National Holiday, Plant Shutdown"
        )
        self.holiday_name_edit.setToolTip("Short description of this non-working day.")

        self.btn_add_holiday = QPushButton(CFG.ADD_NON_WORKING_DAY_LABEL)
        self.btn_add_holiday.setToolTip("Add the selected date and name as a non-working day.")
        self.btn_delete_holiday = QPushButton(CFG.REMOVE_SELECTED_LABEL)
        self.btn_delete_holiday.setToolTip(
            "Remove the currently selected non-working day from the calendar."
        )
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
        self.calc_days_spin.setMinimum(1)
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

        self.btn_save_calendar.clicked.connect(self.save_calendar)
        self.btn_add_holiday.clicked.connect(self.add_holiday)
        self.btn_delete_holiday.clicked.connect(self.delete_selected_holiday)
        self.btn_calc.clicked.connect(self.run_calendar_calc)
        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_recalc_project.clicked.connect(self.recalc_project_schedule)
