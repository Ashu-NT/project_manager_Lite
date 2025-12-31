from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QSizePolicy
from enum import Enum

class CurrencyType(str, Enum):
    
    XAF = "XAF"              # Central African CFA Franc
    EURO = "EUR"             # Euro
    US_DOLLAR = "USD"        # US Dollar
    GB_POUND = "GBP"         # British Pound Sterling

    INR = "INR"              # Indian Rupee
    JPY = "JPY"              # Japanese Yen
    CNY = "CNY"              # Chinese Yuan
    AUD = "AUD"              # Australian Dollar
    CAD = "CAD"              # Canadian Dollar
    CHF = "CHF"              # Swiss Franc
    NZD = "NZD"              # New Zealand Dollar
    SEK = "SEK"              # Swedish Krona
    NOK = "NOK"              # Norwegian Krone
    DKK = "DKK"              # Danish Krone
    SGD = "SGD"              # Singapore Dollar
    HKD = "HKD"              # Hong Kong Dollar
    ZAR = "ZAR"              # South African Rand
    AED = "AED"              # UAE Dirham
    SAR = "SAR"              # Saudi Riyal
    KES = "KES"              # Kenyan Shilling
    NGN = "NGN"              # Nigerian Naira
    BRL = "BRL"              # Brazilian Real
    MXN = "MXN"              # Mexican Peso
    RUB = "RUB"              # Russian Ruble


class UIConfig:
    """Central UI design system"""
    
    #=========GROUPBOX FONTS============
    GROUPBOX_FONT = QFont()
    GROUPBOX_FONT.setPointSize(24)
    GROUPBOX_FONT.setBold(True)

    # A smaller font used specifically for GroupBox titles (keeps title distinct from body text)
    GROUPBOX_TITLE_FONT = QFont()
    GROUPBOX_TITLE_FONT.setPointSize(10)
    GROUPBOX_TITLE_FONT.setBold(True)

    # =====================
    # Window
    # =====================
    DEFAULT_WINDOW_SIZE = QSize(1200, 700)
    DEFAULT_PROJECT_WINDOW_SIZE = QSize(840, 420)
    MIN_WINDOW_SIZE = QSize(800, 500)
    MIN_WIDTH = 800
    MIN_HEIGHT = 500
    MIN_GANTT_WIDTH = 1200
    MIN_GANTT_HEIGHT = 800
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
    # Resize Policies
    # =====================
    FIXED = QSizePolicy.Fixed
    GROW = QSizePolicy.Expanding
    PREFERRED = QSizePolicy.Preferred
    
    # =====================
    # Size Policies (Semantic)
    # =====================
    H_EXPAND_V_FIXED = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    EXPAND_BOTH = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    FIXED_BOTH = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    # =====================
    # Button sizing
    # =====================
    BUTTON_HEIGHT = 28
    BUTTON_MIN_WIDTH_SM = 120
    BUTTON_MIN_WIDTH_MD = 160
    BUTTON_MIN_WIDTH_LG = 200

    # =====================
    # Button size policies
    # =====================
    BTN_FIXED_HEIGHT = QSizePolicy(
        QSizePolicy.Preferred,
        QSizePolicy.Fixed)
    
    # =====================
    # Combo boxes
    # =====================
    COMBO_EDITABLE = True
    COMBO_MAX_VISIBLE = 10
    COMBO_MIN_WIDTH_MD = 160
    
    # =====================
    # Check Box size policies
    # =====================
    CHKBOX_FIXED_HEIGHT = QSizePolicy(
        QSizePolicy.Preferred,
        QSizePolicy.Fixed)


    # =====================
    # Input sizing
    # =====================
    INPUT_HEIGHT = 28
    INPUT_MIN_WIDTH = 160
    TEXTEDIT_MIN_HEIGHT = 120

    # =====================
    # Size policies
    # =====================
    INPUT_POLICY = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    TEXTEDIT_POLICY = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    #====================
    # CHECKBOXES
    #====================
    CHECKBOX_HEIGHT = 20
    CHECKBOX_POLICY = QSizePolicy(
        QSizePolicy.Preferred,
        QSizePolicy.Fixed
    )
    
    # =====================
    # Numeric inputs
    # =====================
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
    # Dates
    # =====================
    DATE_FORMAT = "yyyy-MM-dd"

    # =====================
    # Alignment
    # =====================
    ALIGN_RIGHT = Qt.AlignRight
    ALIGN_LEFT = Qt.AlignLeft
    ALIGN_CENTER = Qt.AlignVCenter
    ALIGN_TOP = Qt.AlignTop
    
    # =====================
    # List widgets
    # =====================
    LIST_MIN_HEIGHT = 180
    LIST_POLICY = QSizePolicy(
        QSizePolicy.Expanding,
        QSizePolicy.Expanding
    )

    # =====================
    # Texts / Labels / Reusable strings
    # Keep UI-visible strings here to avoid hardcoding across tabs
    # =====================
    LABOR_GROUP_TITLE = "Labor"
    LABOR_DETAILS_BUTTON_LABEL = "Labor details"
    LABOR_PER_RESOURCE_TITLE = "Per-resource labor costs (hours × hourly rate):"
    NO_LABOR_ASSIGNMENTS_TEXT = "No labor assignments"
    LABOR_TOTAL_HOURS_LABEL = "Total hours"

    # explanatory note when manual labor items are ignored by computed labor
    LABOR_IGNORED_NOTE = (
        "IGNORE cost items are ignored when computed labor from assignments exists; "
        "computed labor + Manual labor is used for cost summaries. Use 'Labor details' for a per-resource breakdown."
    )

    # generic button labels (can be overridden per dialog)
    SHOW_ASSIGNMENTS_BUTTON_LABEL = "Show assignments"
    CLOSE_BUTTON_LABEL = "Close"
    REFRESH_BUTTON_LABEL = "Refresh"
    RELOAD_BUTTON_LABEL = "Reload"
   
    # =====================
    # Table headers & styles
    # =====================
    LABOR_SUMMARY_HEADERS = ["Resource", "Task", "Actual Hours", "Hourly Rate", "Currency", "Actual Cost"]

    # Styles for muted notes and helper text
    NOTE_STYLE_SHEET = "color: gray; font-style: italic;"

    # Maximum height for compact summary tables so UI remains tidy
    SUMMARY_TABLE_MAX_HEIGHT = 300

    # ---------------------
    # Common button labels
    # ---------------------
    RELOAD_BUTTON_LABEL = "Reload"
    RELOAD_PROJECTS_LABEL = "Reload projects"
    REFRESH_BUTTON_LABEL = "Refresh"
    CLOSE_BUTTON_LABEL = "Close"
    ADD_BUTTON_LABEL = "Add"
    REMOVE_SELECTED_LABEL = "Remove selected"
    EDIT_LABEL = "Edit"
    DELETE_LABEL = "Delete"

    # ---------------------
    # Report actions
    # ---------------------
    SHOW_KPIS_LABEL = "Show KPIs"
    SHOW_GANTT_LABEL = "Show Gantt"
    SHOW_CRITICAL_PATH_LABEL = "Show critical path"
    SHOW_RESOURCE_LOAD_LABEL = "Show resource load"
    EXPORT_GANTT_LABEL = "Export Gantt (PNG)"
    EXPORT_EXCEL_LABEL = "Export Excel"
    EXPORT_PDF_LABEL = "Export PDF"

    # ---------------------
    # Resource tab labels
    # ---------------------
    EDIT_HOURS_LABEL = "Edit hours"
    NEW_RESOURCE_LABEL = "New resource"
    TOGGLE_ACTIVE_LABEL = "Toggle active"
    SHOW_ASSIGNMENTS_IN_PROJECT_LABEL = "Show assignments in project"
    REFRESH_RESOURCES_LABEL = "Refresh resources"

    # ---------------------
    # Cost tab labels
    # ---------------------
    NEW_COST_ITEM_LABEL = "New cost item"
    REFRESH_COSTS_LABEL = "Refresh"

    # ---------------------
    # Task tab labels
    # ---------------------
    NEW_TASK_LABEL = "New task"
    UPDATE_PROGRESS_LABEL = "Update progress"
    DEPENDENCIES_LABEL = "Dependencies..."
    ASSIGNMENTS_LABEL = "Assignments..."
    REFRESH_TASKS_LABEL = "Refresh"

    # ---------------------
    # Project tab labels
    # ---------------------
    NEW_PROJECT_LABEL = "New project"
    REFRESH_PROJECTS_LABEL = "Refresh"
    PROJECT_RESOURCES_LABEL = "Project Resources"   

    # ---------------------
    # Dashboard labels
    # ---------------------
    REFRESH_DASHBOARD_LABEL = "Refresh dashboard"
    CREATE_BASELINE_LABEL = "Create baseline"
    DELETE_BASELINE_LABEL = "Delete baseline"

    # ---------------------
    # Calendar labels
    # ---------------------
    APPLY_WORKING_TIME_LABEL = "Apply working time"
    ADD_NON_WORKING_DAY_LABEL = "Add non-working day"
    REMOVE_SELECTED_LABEL = "Remove selected"
    CALCULATE_LABEL = "Calculate"
    RECALCULATE_SCHEDULE_LABEL = "Recalculate schedule"

    # =====================
    # Reusable style snippets (styleSheet strings)
    # =====================
    INFO_TEXT_STYLE = "color: gray;"
    NOTE_STYLE_SHEET = "color: gray; font-style: italic;"
    SECTION_BOLD_MARGIN_STYLE = "font-weight: bold; margin-top: 8px;"
    TITLE_LARGE_STYLE = "font-size: 16px; font-weight: bold;"

    # Dashboard-specific styles
    DASHBOARD_SUMMARY_STYLE = "font-size: 10pt; color: #555555;"
    DASHBOARD_PROJECT_TITLE_STYLE = "font-size: 10pt; font-weight: 700; color: #222222;"
    DASHBOARD_PROJECT_LABEL = "Project Name:"
    DASHBOARD_PROJECT_LABEL_STYLE = "font-size: 10pt; color: #666666;"

    # Visual box for the project summary area (title + meta chips)
    PROJECT_SUMMARY_BOX_STYLE = "background-color: #ffffff; border: 1px solid #e8e8e8; border-radius: 8px; padding: 8px;"

    # Small fixed height for project summary items (prefix/title/meta) — controls only the vertical size
    DASHBOARD_PROJECT_ITEM_HEIGHT = 32

    # Meta chips are now shown as inline muted text (no separate background boxes)
    DASHBOARD_PROJECT_META_STYLE = "color: #666666; font-size:9pt; padding: 0 4px;"
    DASHBOARD_META_START_PREFIX = "Start:"
    DASHBOARD_META_END_PREFIX = "End:"
    DASHBOARD_META_DURATION_PREFIX = "Duration:"
    DASHBOARD_KPI_TITLE_STYLE = "font-size: 10pt; color: #666666;"
    DASHBOARD_KPI_VALUE_TEMPLATE = "font-size: 12pt; font-weight: bold; color: {color};"
    DASHBOARD_METRIC_BOLD_TEMPLATE = "font-size: 10pt; font-weight: bold; color: {color};"
    DASHBOARD_HIGHLIGHT_COLOR = "#110BD1"
    DASHBOARD_KPI_SUB_STYLE = "font-size: 8pt; color: #999999;"

    # EVM metric colors: customize per-metric colors for the EVM panel
    EVM_METRIC_COLORS = {
        "CPI": "#1e8e3e",  # green
        "SPI": "#1e8e3e",  # green
        "PV": "#4a90e2",   # blue
        "EV": "#4a90e2",   # blue
        "AC": "#d0021b",   # red
        "EAC": "#d0021b",  # red
        "VAC": "#f5a623",  # orange
        "TCPI": "#7f3fbf", # purple
    }
    EVM_DEFAULT_COLOR = DASHBOARD_HIGHLIGHT_COLOR

    # Chart titles
    CHART_TITLE_STYLE = "font-size: 12pt; font-weight: bold;"

    # Table headers used across several tabs
    HOLIDAY_TABLE_HEADERS = ["Date", "Name"]

    # Table headers used in dialogs
    CRITICAL_PATH_HEADERS = ["Task name", "Start", "Finish", "Duration (days)", "Total float", "Status"]
    UPCOMING_TASKS_HEADERS = ["Task", "Start", "Finish", "Progress", "Main resource"]
    RESOURCE_LOAD_HEADERS = ["Resource", "Total allocation (%)", "Tasks count"]

