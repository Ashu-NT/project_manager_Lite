from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from ui.styles.ui_config import UIConfig as CFG


def build_status_row(label: QLabel, accent: str) -> QWidget:
    label.setWordWrap(True)
    label.setTextFormat(Qt.PlainText)
    label.setTextInteractionFlags(Qt.TextSelectableByMouse)
    label.setStyleSheet(
        f"""
        font-size: 9.5pt;
        font-weight: 500;
        color: {CFG.COLOR_TEXT_PRIMARY};
        background: transparent;
        border: none;
        """
    )

    row = QWidget()
    row.setObjectName("evmStatusRow")
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    row.setMinimumHeight(40)
    layout = QVBoxLayout(row)
    layout.setContentsMargins(10, 7, 10, 7)
    layout.setSpacing(0)
    layout.addWidget(label)
    row.setStyleSheet(
        f"""
        QWidget#evmStatusRow {{
            background-color: {CFG.COLOR_BG_SURFACE_ALT};
            border: 1px solid {CFG.COLOR_BORDER};
            border-left: 4px solid {accent};
            border-radius: 8px;
        }}
        """
    )
    return row


def build_metric_row(title_label: QLabel, value_label: QLabel, color: str) -> QWidget:
    title_label.setStyleSheet(
        f"font-size: 9pt; font-weight: 600; color: {CFG.COLOR_TEXT_SECONDARY};"
    )
    title_label.setWordWrap(False)
    value_label.setStyleSheet(
        f"font-size: 11pt; font-weight: 800; color: {color};"
    )
    value_label.setWordWrap(False)
    value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

    row = QWidget()
    row.setObjectName("evmMetricRow")
    row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
    row.setMinimumHeight(36)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(10, 5, 10, 5)
    layout.setSpacing(CFG.SPACING_XS)
    layout.addWidget(title_label)
    layout.addStretch(1)
    layout.addWidget(value_label)
    row.setStyleSheet(
        f"""
        QWidget#evmMetricRow {{
            background-color: {CFG.COLOR_BG_SURFACE_ALT};
            border: 1px solid {CFG.COLOR_BORDER};
            border-left: 4px solid {color};
            border-radius: 8px;
        }}
        QWidget#evmMetricRow QLabel {{
            background: transparent;
            border: none;
        }}
        """
    )
    return row


__all__ = ["build_metric_row", "build_status_row"]
