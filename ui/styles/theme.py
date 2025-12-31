# ui/theme.py

from __future__ import annotations
from PySide6.QtWidgets import QApplication

def base_stylesheet() -> str:
    """
    Returns the global QSS stylesheet for the app.
    Keep all visual tuning here.
    """
    return """
    QWidget {
        font-family: "Segoe UI";
        font-size: 10pt;
        color: #333333;
    }

    QMainWindow {
        background-color: #f4f5f7;
    }

    QTabWidget::pane {
        border-top: 1px solid #d0d0d0;
        background: #f4f5f7;
    }

    QTabBar::tab {
        background: #e0e0e0;
        border: 1px solid #c0c0c0;
        padding: 6px 12px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }

    QTabBar::tab:selected {
        background: #ffffff;
        border-bottom: 1px solid #ffffff;
    }

    QGroupBox {
        border: 1px solid #d0d0d0;
        border-radius: 8px;
        margin-top: 8px;
        background-color: #ffffff;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 8px;
        color: #555555;
        font-weight: 600;
    }

    QPushButton {
        background-color: #4a90e2;
        color: white;
        border-radius: 6px;
        padding: 4px 10px;
        border: 1px solid #357ABD;
    }
    QPushButton:hover {
        background-color: #5aa0f0;
    }
    QPushButton:disabled {
        background-color: #cccccc;
        border-color: #bbbbbb;
        color: #666666;
    }

    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QDateEdit {
        background-color: #ffffff;
        border-radius: 4px;
        border: 1px solid #c8c8c8;
        padding: 2px 4px;
    }
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QDateEdit:focus {
        border: 1px solid #4a90e2;
    }

    QTableWidget {
        background-color: #ffffff;
        alternate-background-color: #f7f9fc;
        border: 1px solid #d0d0d0;
        border-radius: 6px;
    }
    QTableWidget::item {
        padding: 2px 6px;
    }
    QTableWidget::item:selected {
        background-color: #cfe6ff;
        color: #000000;
    }
    QHeaderView::section {
        background-color: #f0f0f0;
        color: #555555;
        padding: 4px 6px;
        border: 0px;
        border-right: 1px solid #d0d0d0;
        font-weight: 600;
    }
    QHeaderView::section:last {
        border-right: 0px;
    }
    """

def apply_app_style(app: QApplication) -> None:
    """
    Apply the global theme to the QApplication.
    Call this once in main().
    """
    app.setStyleSheet(base_stylesheet())