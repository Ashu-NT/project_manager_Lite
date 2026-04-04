from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_meta_chip_style,
)
from ui.platform.shared.styles.ui_config import UIConfig as CFG


def build_maintenance_header(
    *,
    root: QVBoxLayout,
    object_name: str,
    eyebrow_text: str,
    title_text: str,
    subtitle_text: str,
    badges: Sequence[QLabel],
) -> QWidget:
    header = QWidget()
    header.setObjectName(object_name)
    header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
    header.setStyleSheet(
        f"""
        QWidget#{object_name} {{
            background-color: {CFG.COLOR_BG_SURFACE};
            border: 1px solid {CFG.COLOR_BORDER};
            border-radius: 12px;
        }}
        """
    )
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(CFG.MARGIN_SM, CFG.SPACING_XS, CFG.MARGIN_SM, CFG.SPACING_XS)
    header_layout.setSpacing(CFG.SPACING_SM)
    intro = QVBoxLayout()
    intro.setSpacing(CFG.SPACING_XS)
    eyebrow = QLabel(eyebrow_text)
    eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    title = QLabel(title_text)
    title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
    subtitle = QLabel(subtitle_text)
    subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
    subtitle.setWordWrap(True)
    intro.addWidget(eyebrow)
    intro.addWidget(title)
    intro.addWidget(subtitle)
    header_layout.addLayout(intro, 1)

    badges_widget = QWidget()
    badges_layout = QGridLayout(badges_widget)
    badges_layout.setContentsMargins(0, 0, 0, 0)
    badges_layout.setHorizontalSpacing(CFG.SPACING_XS)
    badges_layout.setVerticalSpacing(CFG.SPACING_XS)
    for index, badge in enumerate(badges):
        badges_layout.addWidget(badge, index // 2, index % 2, 1, 1, Qt.AlignRight)
    header_layout.addWidget(badges_widget, 0, Qt.AlignTop | Qt.AlignRight)
    root.addWidget(header)
    return header


def make_accent_badge(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
    return label


def make_meta_badge(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet(dashboard_meta_chip_style())
    return label


def make_filter_toggle_button(parent: QWidget, *, label: str = "Filters") -> QPushButton:
    button = QPushButton(label, parent)
    button.setFixedHeight(CFG.BUTTON_HEIGHT)
    button.setMinimumWidth(132)
    button.setStyleSheet(dashboard_action_button_style("secondary"))
    button.setIcon(parent.style().standardIcon(QStyle.SP_FileDialogDetailedView))
    return button


def set_filter_panel_visible(*, button: QPushButton, panel: QWidget, visible: bool) -> None:
    panel.setVisible(visible)
    button.setText(" Hide Filters" if visible else " Filters")
    button.setIcon(
        button.style().standardIcon(
            QStyle.SP_ArrowUp if visible else QStyle.SP_FileDialogDetailedView
        )
    )


def reset_combo_options(
    combo: QComboBox,
    *,
    placeholder: str,
    options: Iterable[tuple[str, object]],
    selected_value: object | None = None,
) -> None:
    combo.blockSignals(True)
    combo.clear()
    combo.addItem(placeholder, None)
    for label, value in options:
        combo.addItem(label, value)
    if selected_value is not None:
        index = combo.findData(selected_value)
        if index >= 0:
            combo.setCurrentIndex(index)
    combo.blockSignals(False)


def selected_combo_value(combo: QComboBox) -> str | None:
    value = combo.currentData()
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.isoformat(sep=" ", timespec="minutes")


def display_metric(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


__all__ = [
    "build_maintenance_header",
    "display_metric",
    "format_timestamp",
    "make_filter_toggle_button",
    "make_accent_badge",
    "make_meta_badge",
    "reset_combo_options",
    "selected_combo_value",
    "set_filter_panel_visible",
]
