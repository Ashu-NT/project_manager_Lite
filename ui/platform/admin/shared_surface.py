from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


@dataclass(frozen=True)
class ToolbarButtonSpec:
    attr_name: str
    label: str
    variant: str = "secondary"
    min_width: int | None = None


def build_admin_surface_card(*, object_name: str, alt: bool) -> tuple[QWidget, QVBoxLayout]:
    widget = QWidget()
    widget.setObjectName(object_name)
    background = CFG.COLOR_BG_SURFACE_ALT if alt else CFG.COLOR_BG_SURFACE
    widget.setStyleSheet(
        f"""
        QWidget#{object_name} {{
            background-color: {background};
            border: 1px solid {CFG.COLOR_BORDER};
            border-radius: 12px;
        }}
        """
    )
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
    layout.setSpacing(CFG.SPACING_SM)
    return widget, layout


def build_admin_toolbar_surface(
    target: object,
    root: QVBoxLayout,
    *,
    object_name: str,
    button_specs: Sequence[ToolbarButtonSpec],
    trailing_count: int = 1,
    helper_text: str | None = None,
) -> QWidget:
    surface, layout = build_admin_surface_card(object_name=object_name, alt=True)
    toolbar = QHBoxLayout()
    left_specs = list(button_specs[:-trailing_count] if trailing_count > 0 else button_specs)
    right_specs = list(button_specs[-trailing_count:] if trailing_count > 0 else ())
    for spec in left_specs:
        toolbar.addWidget(_make_toolbar_button(target, spec))
    toolbar.addStretch(1)
    for spec in right_specs:
        toolbar.addWidget(_make_toolbar_button(target, spec))
    layout.addLayout(toolbar)
    if helper_text:
        from PySide6.QtWidgets import QLabel

        helper = QLabel(helper_text)
        helper.setWordWrap(True)
        helper.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        layout.addWidget(helper)
    root.addWidget(surface)
    return surface


def build_admin_table(
    *,
    headers: Sequence[str],
    resize_modes: Sequence[QHeaderView.ResizeMode],
) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(list(headers))
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    style_table(table)
    header = table.horizontalHeader()
    for index, mode in enumerate(resize_modes):
        header.setSectionResizeMode(index, mode)
    return table


def _make_toolbar_button(target: object, spec: ToolbarButtonSpec) -> QPushButton:
    button = QPushButton(spec.label)
    button.setFixedHeight(CFG.BUTTON_HEIGHT)
    button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
    if spec.min_width is not None:
        button.setMinimumWidth(spec.min_width)
    button.setStyleSheet(dashboard_action_button_style(spec.variant))
    setattr(target, spec.attr_name, button)
    return button


__all__ = [
    "ToolbarButtonSpec",
    "build_admin_surface_card",
    "build_admin_table",
    "build_admin_toolbar_surface",
]
