from __future__ import annotations

from ui.styles.ui_config import UIConfig as CFG


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
    QTableView QScrollBar:vertical, QTableWidget QScrollBar:vertical {{
        background: {CFG.COLOR_SCROLLBAR_TRACK};
        width: 12px;
        margin: 2px;
        border-radius: 6px;
    }}
    QTableView QScrollBar::handle:vertical, QTableWidget QScrollBar::handle:vertical {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE};
        min-height: 32px;
        border-radius: 6px;
    }}
    QTableView QScrollBar::handle:vertical:hover, QTableWidget QScrollBar::handle:vertical:hover {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_HOVER};
    }}
    QTableView QScrollBar::handle:vertical:pressed, QTableWidget QScrollBar::handle:vertical:pressed {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_ACTIVE};
    }}
    QTableView QScrollBar:horizontal, QTableWidget QScrollBar:horizontal {{
        background: {CFG.COLOR_SCROLLBAR_TRACK};
        height: 12px;
        margin: 2px;
        border-radius: 6px;
    }}
    QTableView QScrollBar::handle:horizontal, QTableWidget QScrollBar::handle:horizontal {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE};
        min-width: 32px;
        border-radius: 6px;
    }}
    QTableView QScrollBar::handle:horizontal:hover, QTableWidget QScrollBar::handle:horizontal:hover {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_HOVER};
    }}
    QTableView QScrollBar::handle:horizontal:pressed, QTableWidget QScrollBar::handle:horizontal:pressed {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_ACTIVE};
    }}
    QTableView QScrollBar::add-line:vertical, QTableView QScrollBar::sub-line:vertical,
    QTableWidget QScrollBar::add-line:vertical, QTableWidget QScrollBar::sub-line:vertical,
    QTableView QScrollBar::add-line:horizontal, QTableView QScrollBar::sub-line:horizontal,
    QTableWidget QScrollBar::add-line:horizontal, QTableWidget QScrollBar::sub-line:horizontal {{
        width: 0px;
        height: 0px;
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
    QMainWindow, QDialog {{
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
        background: {CFG.COLOR_SCROLLBAR_TRACK};
        width: 12px;
        margin: 2px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE};
        min-height: 28px;
        border-radius: 6px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_HOVER};
    }}
    QScrollBar::handle:vertical:pressed {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_ACTIVE};
    }}
    QScrollBar:horizontal {{
        background: {CFG.COLOR_SCROLLBAR_TRACK};
        height: 12px;
        margin: 2px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE};
        min-width: 28px;
        border-radius: 6px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_HOVER};
    }}
    QScrollBar::handle:horizontal:pressed {{
        background: {CFG.COLOR_SCROLLBAR_HANDLE_ACTIVE};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        height: 0px;
        width: 0px;
    }}
    {table_stylesheet()}
    {calendar_stylesheet()}
    """


__all__ = ["table_stylesheet", "calendar_stylesheet", "base_stylesheet"]
