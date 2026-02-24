from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSizePolicy


class CurrencyType(str, Enum):
    XAF = "XAF"
    EUR = "EUR"
    USD = "USD"
    GBP = "GBP"
    INR = "INR"
    JPY = "JPY"
    CNY = "CNY"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    NZD = "NZD"
    SEK = "SEK"
    NOK = "NOK"
    DKK = "DKK"
    SGD = "SGD"
    HKD = "HKD"
    ZAR = "ZAR"
    AED = "AED"
    SAR = "SAR"
    KES = "KES"
    NGN = "NGN"
    BRL = "BRL"
    MXN = "MXN"
    RUB = "RUB"


class UIConfig:
    """Central UI configuration and design tokens."""

    # =====================
    # Typography
    # =====================
    FONT_FAMILY_PRIMARY = "Segoe UI"
    FONT_SIZE_BODY = 10
    FONT_SIZE_SMALL = 9
    FONT_SIZE_TITLE = 16

    GROUPBOX_FONT = QFont(FONT_FAMILY_PRIMARY, 11)
    GROUPBOX_FONT.setBold(True)

    GROUPBOX_TITLE_FONT = QFont(FONT_FAMILY_PRIMARY, 10)
    GROUPBOX_TITLE_FONT.setBold(True)

    # =====================
    # Color system
    # =====================
    COLOR_BG_APP = "#F4F7FB"
    COLOR_BG_SURFACE = "#FFFFFF"
    COLOR_BG_SURFACE_ALT = "#F8FAFC"
    COLOR_BORDER = "#D7E0EA"
    COLOR_BORDER_STRONG = "#C7D2DE"

    COLOR_TEXT_PRIMARY = "#1F2937"
    COLOR_TEXT_SECONDARY = "#4B5563"
    COLOR_TEXT_MUTED = "#6B7280"

    COLOR_ACCENT = "#1D4ED8"
    COLOR_ACCENT_HOVER = "#1E40AF"
    COLOR_ACCENT_PRESSED = "#1E3A8A"
    COLOR_ACCENT_SOFT = "#DBEAFE"

    COLOR_SUCCESS = "#0F766E"
    COLOR_WARNING = "#B45309"
    COLOR_DANGER = "#B42318"
    COLOR_SCROLLBAR_TRACK = "#E2E8F0"
    COLOR_SCROLLBAR_HANDLE = "#94A3B8"
    COLOR_SCROLLBAR_HANDLE_HOVER = "#64748B"
    COLOR_SCROLLBAR_HANDLE_ACTIVE = "#475569"

    # =====================
    # Window
    # =====================
    DEFAULT_WINDOW_SIZE = QSize(1200, 700)
    DEFAULT_PROJECT_WINDOW_SIZE = QSize(840, 420)
    MIN_WINDOW_SIZE = QSize(800, 500)
    MIN_WIDTH = 800
    MIN_HEIGHT = 500
    MIN_GANTT_WIDTH = 1200
    MIN_GANTT_HEIGHT = 700
    MIN_ASSIGNMENTS_WIDTH = 600
    MIN_DEPENDENCIES_WIDTH = 600

    # =====================
    # Spacing
    # =====================
    SPACING_XS = 4
    SPACING_SM = 8
    SPACING_MD = 12
    SPACING_LG = 24

    MARGIN_SM = 8
    MARGIN_MD = 12
    MARGIN_LG = 24
    MARGIN_XL = 32

    # =====================
    # Size policy helpers
    # =====================
    FIXED = QSizePolicy.Fixed
    GROW = QSizePolicy.Expanding
    PREFERRED = QSizePolicy.Preferred

    H_EXPAND_V_FIXED = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    EXPAND_BOTH = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    FIXED_BOTH = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    BTN_FIXED_HEIGHT = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    CHKBOX_FIXED_HEIGHT = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    INPUT_POLICY = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    TEXTEDIT_POLICY = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    LIST_POLICY = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    CHECKBOX_POLICY = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    # =====================
    # Control sizing
    # =====================
    BUTTON_HEIGHT = 30
    BUTTON_MIN_WIDTH_SM = 120
    BUTTON_MIN_WIDTH_MD = 160
    BUTTON_MIN_WIDTH_LG = 200

    COMBO_EDITABLE = True
    COMBO_MAX_VISIBLE = 10
    COMBO_MIN_WIDTH_MD = 160

    INPUT_HEIGHT = 30
    INPUT_MIN_WIDTH = 160
    TEXTEDIT_MIN_HEIGHT = 120
    LIST_MIN_HEIGHT = 180
    CHECKBOX_HEIGHT = 20

    # =====================
    # Numeric inputs
    # =====================
    DEFAULT_CURRENCY_CODE = CurrencyType.EUR.value

    MONEY_DECIMALS = 2
    MONEY_STEP = 100.0
    MONEY_MIN = 0.0
    MONEY_MAX = 1_000_000_000.0

    MIN_VALUE = 0
    PERCENTAGE_MAX = 100.0
    PERCENTAGE_STEP = 10
    PERCENT_DECIMALS = 1
    PRIORITY_MAX = 100
    DURATION_MAX = 3650
    LAG_MAX = 365
    LAG_MIN = -365
    ALLOC_SET_VALUE = 50.0

    WORKING_HOURS_IN_DAY = 8
    MAX_WORKING_HOURS = 24
    MIN_WORKING_HOURS = 1

    # =====================
    # Date and alignment
    # =====================
    DATE_FORMAT = "yyyy-MM-dd"

    ALIGN_RIGHT = Qt.AlignRight
    ALIGN_LEFT = Qt.AlignLeft
    ALIGN_CENTER = Qt.AlignVCenter
    ALIGN_TOP = Qt.AlignTop

    # =====================
    # Common labels
    # =====================
    RELOAD_BUTTON_LABEL = "Reload"
    RELOAD_PROJECTS_LABEL = "Reload Projects"
    REFRESH_BUTTON_LABEL = "Refresh"
    CLOSE_BUTTON_LABEL = "Close"
    ADD_BUTTON_LABEL = "Add"
    REMOVE_SELECTED_LABEL = "Remove Selected"
    EDIT_LABEL = "Edit"
    DELETE_LABEL = "Delete"

    # =====================
    # Report actions
    # =====================
    SHOW_KPIS_LABEL = "Show KPIs"
    SHOW_GANTT_LABEL = "Show Gantt"
    SHOW_CRITICAL_PATH_LABEL = "Show Critical Path"
    SHOW_RESOURCE_LOAD_LABEL = "Show Resource Load"
    EXPORT_GANTT_LABEL = "Export Gantt (PNG)"
    EXPORT_EXCEL_LABEL = "Export Excel"
    EXPORT_PDF_LABEL = "Export PDF"

    # =====================
    # Resource tab labels
    # =====================
    EDIT_HOURS_LABEL = "Edit Hours"
    NEW_RESOURCE_LABEL = "New Resource"
    TOGGLE_ACTIVE_LABEL = "Toggle Active"
    SHOW_ASSIGNMENTS_IN_PROJECT_LABEL = "Show Assignments in Project"
    REFRESH_RESOURCES_LABEL = "Refresh Resources"
    SHOW_ASSIGNMENTS_BUTTON_LABEL = "Show Assignments"

    # =====================
    # Cost tab labels
    # =====================
    NEW_COST_ITEM_LABEL = "New Cost Item"
    REFRESH_COSTS_LABEL = "Refresh Costs"
    LABOR_GROUP_TITLE = "Labor"
    LABOR_DETAILS_BUTTON_LABEL = "Labor Details"
    LABOR_PER_RESOURCE_TITLE = "Per-resource labor costs (hours x hourly rate):"
    NO_LABOR_ASSIGNMENTS_TEXT = "No labor assignments"
    LABOR_TOTAL_HOURS_LABEL = "Total hours"
    LABOR_IGNORED_NOTE = (
        "Manual LABOR cost items are excluded when assignment-based labor exists "
        "to avoid double counting."
    )

    # =====================
    # Task tab labels
    # =====================
    NEW_TASK_LABEL = "New Task"
    UPDATE_PROGRESS_LABEL = "Update Progress"
    DEPENDENCIES_LABEL = "Dependencies"
    ASSIGNMENTS_LABEL = "Assignments..."
    REFRESH_TASKS_LABEL = "Refresh Tasks"

    # =====================
    # Project tab labels
    # =====================
    NEW_PROJECT_LABEL = "New Project"
    REFRESH_PROJECTS_LABEL = "Refresh Projects"
    PROJECT_RESOURCES_LABEL = "Project Resources"

    # =====================
    # Dashboard labels
    # =====================
    REFRESH_DASHBOARD_LABEL = "Refresh Dashboard"
    CREATE_BASELINE_LABEL = "Create Baseline"
    DELETE_BASELINE_LABEL = "Delete Baseline"

    # =====================
    # Calendar labels
    # =====================
    APPLY_WORKING_TIME_LABEL = "Apply Working Time"
    ADD_NON_WORKING_DAY_LABEL = "Add Non-working Day"
    CALCULATE_LABEL = "Calculate"
    RECALCULATE_SCHEDULE_LABEL = "Recalculate Schedule"

    # =====================
    # Shared style snippets
    # =====================
    INFO_TEXT_STYLE = f"color: {COLOR_TEXT_SECONDARY}; font-size: 10pt;"
    NOTE_STYLE_SHEET = f"color: {COLOR_TEXT_SECONDARY}; font-size: 9pt; font-style: italic;"
    SECTION_BOLD_MARGIN_STYLE = f"font-weight: 700; color: {COLOR_TEXT_SECONDARY}; margin-top: 8px;"
    TITLE_LARGE_STYLE = f"font-size: {FONT_SIZE_TITLE}px; font-weight: 700; color: {COLOR_TEXT_PRIMARY};"

    DASHBOARD_SUMMARY_STYLE = f"font-size: 10pt; color: {COLOR_TEXT_SECONDARY};"
    DASHBOARD_PROJECT_LABEL = "Project:"
    DASHBOARD_PROJECT_LABEL_STYLE = f"font-size: 10pt; color: {COLOR_TEXT_MUTED};"
    DASHBOARD_PROJECT_TITLE_STYLE = f"font-size: 11pt; font-weight: 700; color: {COLOR_TEXT_PRIMARY};"
    DASHBOARD_PROJECT_ITEM_HEIGHT = 30
    DASHBOARD_PROJECT_META_STYLE = f"color: {COLOR_TEXT_MUTED}; font-size: 9pt; padding: 0 6px;"
    DASHBOARD_META_START_PREFIX = "Start:"
    DASHBOARD_META_END_PREFIX = "End:"
    DASHBOARD_META_DURATION_PREFIX = "Duration:"

    PROJECT_SUMMARY_BOX_STYLE = (
        f"background-color: {COLOR_BG_SURFACE}; "
        f"border: 1px solid {COLOR_BORDER}; border-radius: 10px; padding: 8px;"
    )

    DASHBOARD_KPI_TITLE_STYLE = f"font-size: 9pt; color: {COLOR_TEXT_MUTED};"
    DASHBOARD_KPI_VALUE_TEMPLATE = "font-size: 14pt; font-weight: 700; color: {color};"
    DASHBOARD_METRIC_BOLD_TEMPLATE = "font-size: 10pt; font-weight: 700; color: {color};"
    DASHBOARD_KPI_SUB_STYLE = f"font-size: 8pt; color: {COLOR_TEXT_MUTED};"
    DASHBOARD_HIGHLIGHT_COLOR = COLOR_ACCENT

    CHART_TITLE_STYLE = f"font-size: 11pt; font-weight: 700; color: {COLOR_TEXT_SECONDARY};"

    # =====================
    # Table headers
    # =====================
    HOLIDAY_TABLE_HEADERS = ["Date", "Name"]
    LABOR_SUMMARY_HEADERS = ["Resource", "Task", "Actual Hours", "Hourly Rate", "Currency", "Actual Cost"]
    CRITICAL_PATH_HEADERS = ["Task Name", "Start", "Finish", "Duration (days)", "Total Float", "Status"]
    UPCOMING_TASKS_HEADERS = ["Task", "Start", "Finish", "Progress", "Main Resource"]
    RESOURCE_LOAD_HEADERS = ["Resource", "Total Allocation (%)", "Tasks Count"]

    SUMMARY_TABLE_MAX_HEIGHT = 300

    # =====================
    # EVM colors
    # =====================
    EVM_METRIC_COLORS = {
        "CPI": COLOR_SUCCESS,
        "SPI": COLOR_SUCCESS,
        "PV": COLOR_ACCENT,
        "EV": COLOR_ACCENT,
        "AC": COLOR_DANGER,
        "EAC": COLOR_DANGER,
        "VAC": COLOR_WARNING,
        "TCPI": COLOR_TEXT_SECONDARY,
        "TCPI_EAC": COLOR_TEXT_SECONDARY,
    }
    EVM_DEFAULT_COLOR = DASHBOARD_HIGHLIGHT_COLOR
