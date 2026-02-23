from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.styles.ui_config import UIConfig as CFG


LIGHT_THEME = {
    "COLOR_BG_APP": "#F4F7FB",
    "COLOR_BG_SURFACE": "#FFFFFF",
    "COLOR_BG_SURFACE_ALT": "#F8FAFC",
    "COLOR_BORDER": "#D7E0EA",
    "COLOR_BORDER_STRONG": "#C7D2DE",
    "COLOR_TEXT_PRIMARY": "#1F2937",
    "COLOR_TEXT_SECONDARY": "#4B5563",
    "COLOR_TEXT_MUTED": "#6B7280",
    "COLOR_ACCENT": "#1D4ED8",
    "COLOR_ACCENT_HOVER": "#1E40AF",
    "COLOR_ACCENT_PRESSED": "#1E3A8A",
    "COLOR_ACCENT_SOFT": "#DBEAFE",
    "COLOR_SUCCESS": "#0F766E",
    "COLOR_WARNING": "#B45309",
    "COLOR_DANGER": "#B42318",
}


DARK_THEME = {
    "COLOR_BG_APP": "#0B1220",
    "COLOR_BG_SURFACE": "#111A2C",
    "COLOR_BG_SURFACE_ALT": "#16243A",
    "COLOR_BORDER": "#29405C",
    "COLOR_BORDER_STRONG": "#36527A",
    "COLOR_TEXT_PRIMARY": "#E5EDF8",
    "COLOR_TEXT_SECONDARY": "#B9C7DC",
    "COLOR_TEXT_MUTED": "#91A4C2",
    "COLOR_ACCENT": "#60A5FA",
    "COLOR_ACCENT_HOVER": "#3B82F6",
    "COLOR_ACCENT_PRESSED": "#2563EB",
    "COLOR_ACCENT_SOFT": "#1E3A5F",
    "COLOR_SUCCESS": "#34D399",
    "COLOR_WARNING": "#F59E0B",
    "COLOR_DANGER": "#F87171",
}


def _apply_theme_tokens(mode: str = "light") -> None:
    normalized = (mode or "light").strip().lower()
    palette = DARK_THEME if normalized == "dark" else LIGHT_THEME
    for attr, value in palette.items():
        setattr(CFG, attr, value)

    CFG.INFO_TEXT_STYLE = f"color: {CFG.COLOR_TEXT_MUTED}; font-size: 9pt;"
    CFG.NOTE_STYLE_SHEET = (
        f"color: {CFG.COLOR_TEXT_MUTED}; font-size: 9pt; font-style: italic;"
    )
    CFG.SECTION_BOLD_MARGIN_STYLE = (
        f"font-weight: 700; color: {CFG.COLOR_TEXT_SECONDARY}; margin-top: 8px;"
    )
    CFG.TITLE_LARGE_STYLE = (
        f"font-size: {CFG.FONT_SIZE_TITLE}px; font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY};"
    )

    CFG.DASHBOARD_SUMMARY_STYLE = f"font-size: 10pt; color: {CFG.COLOR_TEXT_SECONDARY};"
    CFG.DASHBOARD_PROJECT_LABEL_STYLE = f"font-size: 10pt; color: {CFG.COLOR_TEXT_MUTED};"
    CFG.DASHBOARD_PROJECT_TITLE_STYLE = (
        f"font-size: 11pt; font-weight: 700; color: {CFG.COLOR_TEXT_PRIMARY};"
    )
    CFG.DASHBOARD_PROJECT_META_STYLE = (
        f"color: {CFG.COLOR_TEXT_MUTED}; font-size: 9pt; padding: 0 6px;"
    )
    CFG.PROJECT_SUMMARY_BOX_STYLE = (
        f"background-color: {CFG.COLOR_BG_SURFACE}; "
        f"border: 1px solid {CFG.COLOR_BORDER}; border-radius: 10px; padding: 8px;"
    )
    CFG.DASHBOARD_KPI_TITLE_STYLE = f"font-size: 9pt; color: {CFG.COLOR_TEXT_MUTED};"
    CFG.DASHBOARD_KPI_SUB_STYLE = f"font-size: 8pt; color: {CFG.COLOR_TEXT_MUTED};"
    CFG.DASHBOARD_HIGHLIGHT_COLOR = CFG.COLOR_ACCENT
    CFG.CHART_TITLE_STYLE = (
        f"font-size: 11pt; font-weight: 700; color: {CFG.COLOR_TEXT_SECONDARY};"
    )
    CFG.EVM_METRIC_COLORS = {
        "CPI": CFG.COLOR_SUCCESS,
        "SPI": CFG.COLOR_SUCCESS,
        "PV": CFG.COLOR_ACCENT,
        "EV": CFG.COLOR_ACCENT,
        "AC": CFG.COLOR_DANGER,
        "EAC": CFG.COLOR_DANGER,
        "VAC": CFG.COLOR_WARNING,
        "TCPI": CFG.COLOR_TEXT_SECONDARY,
        "TCPI_EAC": CFG.COLOR_TEXT_SECONDARY,
    }
    CFG.EVM_DEFAULT_COLOR = CFG.DASHBOARD_HIGHLIGHT_COLOR


def set_theme_mode(mode: str = "light") -> None:
    _apply_theme_tokens(mode)


def table_stylesheet() -> str:
    return f"""
    QTableView, QTableWidget {{
        background-color: {CFG.COLOR_BG_SURFACE};
        alternate-background-color: {CFG.COLOR_BG_SURFACE_ALT};
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 8px;
        gridline-color: {CFG.COLOR_BORDER_STRONG};
        selection-background-color: {CFG.COLOR_ACCENT_SOFT};
        selection-color: {CFG.COLOR_TEXT_PRIMARY};
        outline: 0;
    }}

    QTableView::item, QTableWidget::item {{
        padding: 7px 10px;
        border: 1px solid transparent;
        color: {CFG.COLOR_TEXT_PRIMARY};
    }}

    QTableView::item:selected, QTableWidget::item:selected {{
        background-color: {CFG.COLOR_ACCENT_SOFT};
        color: {CFG.COLOR_TEXT_PRIMARY};
        border: 2px solid {CFG.COLOR_ACCENT};
    }}

    QTableView::item:focus, QTableWidget::item:focus {{
        border: 2px solid {CFG.COLOR_ACCENT_HOVER};
        background-color: {CFG.COLOR_ACCENT_SOFT};
    }}

    QTableView::item:hover, QTableWidget::item:hover {{
        background-color: {CFG.COLOR_BG_SURFACE_ALT};
    }}

    QTableCornerButton::section {{
        background: {CFG.COLOR_BG_SURFACE_ALT};
        border: 1px solid {CFG.COLOR_BORDER};
    }}

    QHeaderView::section {{
        background-color: {CFG.COLOR_BG_SURFACE_ALT};
        color: {CFG.COLOR_TEXT_SECONDARY};
        border: none;
        border-right: 1px solid {CFG.COLOR_BORDER};
        border-bottom: 2px solid {CFG.COLOR_BORDER_STRONG};
        padding: 7px 8px;
        font-weight: 600;
    }}
    """


def calendar_stylesheet() -> str:
    return f"""
    QCalendarWidget {{
        background-color: {CFG.COLOR_BG_SURFACE};
    }}

    QCalendarWidget QTableView {{
        background-color: {CFG.COLOR_BG_SURFACE};
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 8px;
        selection-background-color: {CFG.COLOR_ACCENT_SOFT};
        selection-color: {CFG.COLOR_TEXT_PRIMARY};
        outline: 0;
    }}

    QCalendarWidget QTableView::item {{
        padding: 0px;
        margin: 0px;
    }}

    QCalendarWidget QTableView QHeaderView::section {{
        background-color: {CFG.COLOR_BG_SURFACE_ALT};
        color: {CFG.COLOR_TEXT_SECONDARY};
        border: none;
        padding: 2px 0px;
        font-weight: 600;
    }}

    QCalendarWidget QWidget#qt_calendar_navigationbar {{
        background-color: {CFG.COLOR_BG_SURFACE_ALT};
        border: none;
    }}

    QCalendarWidget QToolButton {{
        color: {CFG.COLOR_TEXT_PRIMARY};
        background: transparent;
        border: none;
        padding: 2px 6px;
        font-weight: 600;
    }}
    """


def base_stylesheet() -> str:
    return f"""
    QWidget {{
        font-family: "{CFG.FONT_FAMILY_PRIMARY}";
        font-size: {CFG.FONT_SIZE_BODY}pt;
        color: {CFG.COLOR_TEXT_PRIMARY};
    }}

    QMainWindow {{
        background-color: {CFG.COLOR_BG_APP};
    }}

    QTabWidget::pane {{
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 10px;
        background: {CFG.COLOR_BG_SURFACE};
        top: -1px;
    }}

    QTabBar::tab {{
        background: {CFG.COLOR_BG_SURFACE_ALT};
        color: {CFG.COLOR_TEXT_SECONDARY};
        border: 1px solid {CFG.COLOR_BORDER};
        border-bottom: none;
        min-width: 120px;
        padding: 7px 14px;
        margin-right: 4px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        font-weight: 600;
    }}

    QTabBar::tab:hover {{
        background: {CFG.COLOR_BG_SURFACE};
        color: {CFG.COLOR_TEXT_PRIMARY};
    }}

    QTabBar::tab:selected {{
        background: {CFG.COLOR_BG_SURFACE};
        color: {CFG.COLOR_TEXT_PRIMARY};
        border-color: {CFG.COLOR_BORDER_STRONG};
    }}

    QGroupBox {{
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 10px;
        margin-top: 10px;
        background-color: {CFG.COLOR_BG_SURFACE};
        padding-top: 8px;
    }}

    QGroupBox::title {{
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 8px;
        margin-left: 8px;
        color: {CFG.COLOR_TEXT_SECONDARY};
        font-weight: 700;
        background: {CFG.COLOR_BG_SURFACE};
    }}

    QPushButton {{
        background-color: {CFG.COLOR_ACCENT};
        color: white;
        border: 1px solid {CFG.COLOR_ACCENT_HOVER};
        border-radius: 7px;
        padding: 5px 12px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background-color: {CFG.COLOR_ACCENT_HOVER};
    }}

    QPushButton:pressed {{
        background-color: {CFG.COLOR_ACCENT_PRESSED};
    }}

    QPushButton:disabled {{
        background-color: {CFG.COLOR_BORDER};
        border-color: {CFG.COLOR_BORDER_STRONG};
        color: {CFG.COLOR_TEXT_MUTED};
    }}

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit, QTextEdit {{
        background-color: {CFG.COLOR_BG_SURFACE};
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 6px;
        padding: 4px 6px;
        color: {CFG.COLOR_TEXT_PRIMARY};
        selection-background-color: {CFG.COLOR_ACCENT_SOFT};
        selection-color: {CFG.COLOR_TEXT_PRIMARY};
    }}

    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus, QTextEdit:focus {{
        border: 1px solid {CFG.COLOR_ACCENT};
    }}

    QComboBox::drop-down {{
        width: 24px;
        border-left: 1px solid {CFG.COLOR_BORDER};
        background: {CFG.COLOR_BG_SURFACE_ALT};
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {CFG.COLOR_BG_SURFACE};
        color: {CFG.COLOR_TEXT_PRIMARY};
        border: 1px solid {CFG.COLOR_BORDER};
        selection-background-color: {CFG.COLOR_ACCENT_SOFT};
        selection-color: {CFG.COLOR_TEXT_PRIMARY};
        outline: 0;
    }}

    QComboBox#themeSwitch {{
        min-width: 120px;
        font-weight: 600;
        color: {CFG.COLOR_TEXT_PRIMARY};
        background-color: {CFG.COLOR_BG_SURFACE_ALT};
        border: 1px solid {CFG.COLOR_BORDER_STRONG};
        padding-right: 10px;
    }}

    QComboBox#themeSwitch::drop-down {{
        width: 26px;
        background: {CFG.COLOR_BG_SURFACE};
        border-left: 1px solid {CFG.COLOR_BORDER};
    }}

    QComboBox#themeSwitch QAbstractItemView {{
        background-color: {CFG.COLOR_BG_SURFACE};
        color: {CFG.COLOR_TEXT_PRIMARY};
        border: 1px solid {CFG.COLOR_BORDER};
        selection-background-color: {CFG.COLOR_ACCENT_SOFT};
        selection-color: {CFG.COLOR_TEXT_PRIMARY};
    }}

    QScrollArea {{
        border: none;
        background: transparent;
    }}

    QListWidget {{
        background-color: {CFG.COLOR_BG_SURFACE};
        border: 1px solid {CFG.COLOR_BORDER};
        border-radius: 8px;
        padding: 4px;
    }}

    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 4px;
    }}

    QListWidget::item:selected {{
        background-color: {CFG.COLOR_ACCENT_SOFT};
        color: {CFG.COLOR_TEXT_PRIMARY};
    }}

    QCheckBox {{
        spacing: 6px;
        color: {CFG.COLOR_TEXT_SECONDARY};
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {CFG.COLOR_BORDER_STRONG};
        border-radius: 3px;
        background: {CFG.COLOR_BG_SURFACE};
    }}

    QCheckBox::indicator:checked {{
        background-color: {CFG.COLOR_ACCENT};
        border-color: {CFG.COLOR_ACCENT};
    }}

    QScrollBar:vertical {{
        background: {CFG.COLOR_BG_SURFACE_ALT};
        width: 10px;
        margin: 2px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical {{
        background: {CFG.COLOR_BORDER_STRONG};
        min-height: 24px;
        border-radius: 5px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {CFG.COLOR_TEXT_MUTED};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    {table_stylesheet()}
    {calendar_stylesheet()}
    """


def apply_app_style(app: QApplication, mode: str = "light") -> None:
    set_theme_mode(mode)
    app.setStyleSheet(base_stylesheet())
