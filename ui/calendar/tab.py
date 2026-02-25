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
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from core.events.domain_events import domain_events
from core.services.auth import UserSessionContext
from core.services.project import ProjectService
from core.services.scheduling import SchedulingEngine
from core.services.task import TaskService
from core.services.work_calendar import WorkCalendarEngine, WorkCalendarService
from ui.calendar.calculator import CalendarCalculatorMixin
from ui.calendar.holidays import CalendarHolidaysMixin
from ui.calendar.project_ops import CalendarProjectOpsMixin
from ui.calendar.working_time import CalendarWorkingTimeMixin
from ui.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
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
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._wc_service: WorkCalendarService = work_calendar_service
        self._wc_engine: WorkCalendarEngine = work_calendar_engine
        self._scheduling_engine: SchedulingEngine = scheduling_engine
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._user_session = user_session
        self._can_manage_calendar = has_permission(self._user_session, "task.manage")

        self._setup_ui()
        self.load_calendar_config()
        self.load_holidays()
        self.reload_projects()
        domain_events.project_changed.connect(self._on_project_changed)

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Calendar & Scheduling")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Configure working days, holidays, and run schedule date calculations from one place."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        root.addWidget(splitter, 1)

        left_container = QWidget()
        left_col = QVBoxLayout(left_container)
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(CFG.SPACING_MD)

        right_container = QWidget()
        right_col = QVBoxLayout(right_container)
        right_col.setContentsMargins(0, 0, 0, 0)
        right_col.setSpacing(CFG.SPACING_MD)

        grp_days = QGroupBox("Working Calendar")
        grp_days.setFont(CFG.GROUPBOX_TITLE_FONT)
        days_layout = QVBoxLayout(grp_days)
        days_layout.setSpacing(CFG.SPACING_SM)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.summary_label.setWordWrap(True)
        days_layout.addWidget(self.summary_label)

        days_row = QHBoxLayout()
        self.day_checks = []
        for index, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            cb = QCheckBox(name)
            cb.setChecked(index < 5)
            cb.day_index = index
            self.day_checks.append(cb)
            days_row.addWidget(cb)
        days_row.addStretch()
        days_layout.addLayout(days_row)

        hours_row = QHBoxLayout()
        hours_row.addWidget(QLabel("Hours/day:"))
        self.hours_spin = QSpinBox()
        self.hours_spin.setMinimum(CFG.MIN_WORKING_HOURS)
        self.hours_spin.setMaximum(CFG.MAX_WORKING_HOURS)
        self.hours_spin.setValue(CFG.WORKING_HOURS_IN_DAY)
        self.hours_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.hours_spin.setMinimumWidth(96)
        self.btn_save_calendar = QPushButton(CFG.APPLY_WORKING_TIME_LABEL)
        self.btn_save_calendar.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_save_calendar.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        hours_row.addWidget(self.hours_spin)
        hours_row.addWidget(self.btn_save_calendar)
        hours_row.addStretch()
        days_layout.addLayout(hours_row)
        left_col.addWidget(grp_days)

        grp_holidays = QGroupBox("Non-working Days")
        grp_holidays.setFont(CFG.GROUPBOX_TITLE_FONT)
        hol_layout = QVBoxLayout(grp_holidays)
        hol_layout.setSpacing(CFG.SPACING_SM)

        self.holiday_table = QTableWidget(0, 2)
        self.holiday_table.setHorizontalHeaderLabels(CFG.HOLIDAY_TABLE_HEADERS)
        self.holiday_table.verticalHeader().setVisible(False)
        self.holiday_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.holiday_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.holiday_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.holiday_table.setMinimumHeight(220)
        style_table(self.holiday_table)
        hol_layout.addWidget(self.holiday_table)

        form_row = QHBoxLayout()
        self.holiday_date_edit = QDateEdit()
        self.holiday_date_edit.setDisplayFormat(CFG.DATE_FORMAT)
        self.holiday_date_edit.setCalendarPopup(True)
        self.holiday_date_edit.setDate(QDate.currentDate())
        self.holiday_date_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.holiday_date_edit.setMinimumWidth(130)
        self.holiday_name_edit = QLineEdit()
        self.holiday_name_edit.setPlaceholderText("Holiday name")
        self.holiday_name_edit.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_add_holiday = QPushButton(CFG.ADD_NON_WORKING_DAY_LABEL)
        self.btn_delete_holiday = QPushButton(CFG.REMOVE_SELECTED_LABEL)
        for btn in (self.btn_add_holiday, self.btn_delete_holiday):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)

        form_row.addWidget(QLabel("Date"))
        form_row.addWidget(self.holiday_date_edit)
        form_row.addWidget(QLabel("Name"))
        form_row.addWidget(self.holiday_name_edit, 1)
        form_row.addWidget(self.btn_add_holiday)
        form_row.addWidget(self.btn_delete_holiday)
        hol_layout.addLayout(form_row)
        left_col.addWidget(grp_holidays, 1)

        grp_calc = QGroupBox("Working-day Calculator")
        grp_calc.setFont(CFG.GROUPBOX_TITLE_FONT)
        calc_layout = QVBoxLayout(grp_calc)
        calc_layout.setSpacing(CFG.SPACING_SM)

        calc_row = QHBoxLayout()
        self.calc_start = QDateEdit()
        self.calc_start.setCalendarPopup(True)
        self.calc_start.setDisplayFormat(CFG.DATE_FORMAT)
        self.calc_start.setDate(QDate.currentDate())
        self.calc_start.setFixedHeight(CFG.INPUT_HEIGHT)
        self.calc_days_spin = QSpinBox()
        self.calc_days_spin.setMinimum(1)
        self.calc_days_spin.setMaximum(3650)
        self.calc_days_spin.setValue(5)
        self.calc_days_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_calc = QPushButton(CFG.CALCULATE_LABEL)
        self.btn_calc.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_calc.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        calc_row.addWidget(QLabel("Start"))
        calc_row.addWidget(self.calc_start)
        calc_row.addWidget(QLabel("Days"))
        calc_row.addWidget(self.calc_days_spin)
        calc_row.addWidget(self.btn_calc)
        calc_row.addStretch()
        calc_layout.addLayout(calc_row)

        self.calc_result_label = QLabel("Result: not calculated.")
        self.calc_result_label.setWordWrap(True)
        self.calc_result_label.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        calc_layout.addWidget(self.calc_result_label)
        right_col.addWidget(grp_calc)

        grp_sched = QGroupBox("Project Schedule Recalculation")
        grp_sched.setFont(CFG.GROUPBOX_TITLE_FONT)
        sched_layout = QVBoxLayout(grp_sched)
        sched_layout.setSpacing(CFG.SPACING_SM)

        project_row = QHBoxLayout()
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(CFG.COMBO_MIN_WIDTH_MD)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        self.btn_recalc_project = QPushButton(CFG.RECALCULATE_SCHEDULE_LABEL)
        for btn in (self.btn_reload_projects, self.btn_recalc_project):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)

        project_row.addWidget(QLabel("Project"))
        project_row.addWidget(self.project_combo, 1)
        project_row.addWidget(self.btn_reload_projects)
        project_row.addWidget(self.btn_recalc_project)
        sched_layout.addLayout(project_row)

        hint = QLabel("Apply after editing working days or holidays to refresh task dates.")
        hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        hint.setWordWrap(True)
        sched_layout.addWidget(hint)
        right_col.addWidget(grp_sched)
        right_col.addStretch()
        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([780, 460])

        self.btn_save_calendar.clicked.connect(
            make_guarded_slot(self, title="Calendar", callback=self.save_calendar)
        )
        self.btn_add_holiday.clicked.connect(
            make_guarded_slot(self, title="Calendar", callback=self.add_holiday)
        )
        self.btn_delete_holiday.clicked.connect(
            make_guarded_slot(self, title="Calendar", callback=self.delete_selected_holiday)
        )
        self.btn_calc.clicked.connect(self.run_calendar_calc)
        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_recalc_project.clicked.connect(
            make_guarded_slot(self, title="Calendar", callback=self.recalc_project_schedule)
        )

        apply_permission_hint(
            self.btn_save_calendar,
            allowed=self._can_manage_calendar,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_add_holiday,
            allowed=self._can_manage_calendar,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_delete_holiday,
            allowed=self._can_manage_calendar,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_recalc_project,
            allowed=self._can_manage_calendar,
            missing_permission="task.manage",
        )
        self.btn_save_calendar.setEnabled(self._can_manage_calendar)
        self.btn_add_holiday.setEnabled(self._can_manage_calendar)
        self.btn_delete_holiday.setEnabled(self._can_manage_calendar)
        self.btn_recalc_project.setEnabled(self._can_manage_calendar)
