from __future__ import annotations

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui.dashboard.styles import dashboard_action_button_style, dashboard_badge_style, dashboard_meta_chip_style
from ui.shared.guards import apply_permission_hint, make_guarded_slot
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class CalendarSurfaceMixin:
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        self.calendar_header_card = header
        header.setObjectName("calendarHeaderCard")
        header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        header.setStyleSheet(
            f"QWidget#calendarHeaderCard {{ background-color: {CFG.COLOR_BG_SURFACE}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        header_layout.setAlignment(Qt.AlignTop)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        for widget in (
            QLabel("CALENDAR"),
            QLabel("Calendar & Scheduling"),
            QLabel("Configure working time, non-working days, and project schedule recalculation from one control surface."),
        ):
            intro.addWidget(widget)
        intro.itemAt(0).widget().setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.itemAt(1).widget().setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.itemAt(2).widget().setStyleSheet(CFG.INFO_TEXT_STYLE)
        intro.itemAt(2).widget().setWordWrap(True)
        intro.itemAt(2).widget().setMaximumWidth(760)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.calendar_scope_badge = QLabel("Mon-Fri | 8h/day")
        self.calendar_scope_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.calendar_holiday_badge = QLabel("0 holidays")
        self.calendar_holiday_badge.setStyleSheet(dashboard_meta_chip_style())
        self.calendar_project_badge = QLabel("No Project")
        self.calendar_project_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_calendar else "Read Only"
        self.calendar_access_badge = QLabel(access_label)
        self.calendar_access_badge.setStyleSheet(dashboard_meta_chip_style())
        for badge in (
            self.calendar_scope_badge,
            self.calendar_holiday_badge,
            self.calendar_project_badge,
            self.calendar_access_badge,
        ):
            status_layout.addWidget(badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        root.addWidget(header)

        controls = QWidget()
        self.calendar_controls_card = controls
        controls.setObjectName("calendarControlSurface")
        controls.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        controls.setStyleSheet(
            f"QWidget#calendarControlSurface {{ background-color: {CFG.COLOR_BG_SURFACE_ALT}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
        )
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)
        controls_layout.addWidget(QLabel("Project"))
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(CFG.COMBO_MIN_WIDTH_MD)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        self.btn_recalc_project = QPushButton(CFG.RECALCULATE_SCHEDULE_LABEL)
        for btn in (self.btn_reload_projects, self.btn_recalc_project):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_reload_projects.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_recalc_project.setStyleSheet(dashboard_action_button_style("primary"))
        controls_layout.addWidget(self.project_combo, 1)
        controls_layout.addWidget(self.btn_reload_projects)
        controls_layout.addWidget(self.btn_recalc_project)
        root.addWidget(controls)

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
        hours_row.addWidget(QLabel("Hours/day"))
        self.hours_spin = QSpinBox()
        self.hours_spin.setMinimum(CFG.MIN_WORKING_HOURS)
        self.hours_spin.setMaximum(CFG.MAX_WORKING_HOURS)
        self.hours_spin.setValue(CFG.WORKING_HOURS_IN_DAY)
        self.hours_spin.setFixedHeight(CFG.INPUT_HEIGHT)
        self.hours_spin.setMinimumWidth(96)
        self.btn_save_calendar = QPushButton(CFG.APPLY_WORKING_TIME_LABEL)
        self.btn_save_calendar.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_save_calendar.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_save_calendar.setStyleSheet(dashboard_action_button_style("primary"))
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
        for btn, variant in (
            (self.btn_add_holiday, "secondary"),
            (self.btn_delete_holiday, "danger"),
        ):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setStyleSheet(dashboard_action_button_style(variant))
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
        self.btn_calc.setStyleSheet(dashboard_action_button_style("secondary"))
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
        right_col.addStretch()

        splitter.addWidget(left_container)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([780, 460])

        self.btn_save_calendar.clicked.connect(make_guarded_slot(self, title="Calendar", callback=self.save_calendar))
        self.btn_add_holiday.clicked.connect(make_guarded_slot(self, title="Calendar", callback=self.add_holiday))
        self.btn_delete_holiday.clicked.connect(make_guarded_slot(self, title="Calendar", callback=self.delete_selected_holiday))
        self.btn_calc.clicked.connect(self.run_calendar_calc)
        self.btn_reload_projects.clicked.connect(self.reload_projects)
        self.btn_recalc_project.clicked.connect(make_guarded_slot(self, title="Calendar", callback=self.recalc_project_schedule))
        self.project_combo.currentTextChanged.connect(lambda _text: self._update_calendar_header_badges())

        for btn in (self.btn_save_calendar, self.btn_add_holiday, self.btn_delete_holiday, self.btn_recalc_project):
            apply_permission_hint(btn, allowed=self._can_manage_calendar, missing_permission="task.manage")
            btn.setEnabled(self._can_manage_calendar)
        self._update_calendar_header_badges(
            working_days={0, 1, 2, 3, 4},
            hours_per_day=8.0,
            holiday_count=0,
            project_name="No Project",
        )

    def _update_calendar_header_badges(
        self,
        *,
        working_days: set[int] | None = None,
        hours_per_day: float | None = None,
        holiday_count: int | None = None,
        project_name: str | None = None,
    ) -> None:
        if working_days is not None:
            self._calendar_badge_days = set(working_days)
        if hours_per_day is not None:
            self._calendar_badge_hours = float(hours_per_day)
        if holiday_count is not None:
            self._calendar_badge_holidays = int(holiday_count)
        if project_name is not None:
            self._calendar_badge_project = project_name.strip() or "No Project"
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        active = [day_names[i] for i in sorted(getattr(self, "_calendar_badge_days", {0, 1, 2, 3, 4}))]
        scope = f"{'/'.join(active) if active else 'No days'} | {getattr(self, '_calendar_badge_hours', 8.0):g}h/day"
        self.calendar_scope_badge.setText(scope)
        self.calendar_holiday_badge.setText(f"{getattr(self, '_calendar_badge_holidays', 0)} holidays")
        self.calendar_project_badge.setText(getattr(self, "_calendar_badge_project", "No Project"))
