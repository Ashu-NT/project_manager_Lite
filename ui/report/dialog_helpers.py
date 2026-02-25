from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QDialog, QFormLayout, QGroupBox, QLabel, QVBoxLayout, QWidget

from ui.styles.ui_config import UIConfig as CFG


def metric_card(title: str, value: str, subtitle: str = "", color: str | None = None) -> QWidget:
    card = QWidget()
    card.setObjectName("metricCard")
    card.setStyleSheet(
        f"""
        QWidget#metricCard {{
            background-color: {CFG.COLOR_BG_SURFACE};
            border: 1px solid {CFG.COLOR_BORDER};
            border-radius: 10px;
        }}
        QWidget#metricCard QLabel {{
            background: transparent;
            border: none;
        }}
        """
    )
    layout = QVBoxLayout(card)
    layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
    layout.setSpacing(2)

    lbl_title = QLabel(title)
    lbl_title.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    lbl_value = QLabel(value)
    lbl_value.setStyleSheet(
        CFG.DASHBOARD_KPI_VALUE_TEMPLATE.format(color=color or CFG.COLOR_TEXT_PRIMARY)
    )
    lbl_sub = QLabel(subtitle)
    lbl_sub.setStyleSheet(CFG.DASHBOARD_KPI_SUB_STYLE)
    lbl_sub.setWordWrap(True)
    lbl_sub.setVisible(bool(subtitle))

    layout.addWidget(lbl_title)
    layout.addWidget(lbl_value)
    layout.addWidget(lbl_sub)
    layout.addStretch()
    return card


def section_group(title: str, rows: list[tuple[str, str]]) -> QGroupBox:
    group = QGroupBox(title)
    group.setFont(CFG.GROUPBOX_TITLE_FONT)

    form = QFormLayout(group)
    form.setLabelAlignment(CFG.ALIGN_LEFT | CFG.ALIGN_CENTER)
    form.setFormAlignment(CFG.ALIGN_TOP)
    form.setHorizontalSpacing(CFG.SPACING_MD)
    form.setVerticalSpacing(CFG.SPACING_SM)
    form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.DontWrapRows)

    for label, value in rows:
        v = QLabel(value)
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow(label, v)

    return group


def setup_dialog_size(
    dialog: QDialog,
    min_width: int,
    min_height: int,
    width: int,
    height: int,
) -> None:
    dialog.setMinimumWidth(min_width)
    dialog.setMinimumHeight(min_height)
    dialog.resize(width, height)


def soft_brush(hex_color: str, alpha: int) -> QBrush:
    color = QColor(hex_color)
    color.setAlpha(max(0, min(alpha, 255)))
    return QBrush(color)


def fmt_money_or_dash(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value):,.2f}"
