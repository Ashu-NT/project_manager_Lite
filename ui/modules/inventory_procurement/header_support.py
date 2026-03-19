from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.platform.shared.styles.ui_config import UIConfig as CFG


def configure_inventory_header_layout(*, header_layout: QHBoxLayout, intro_layout: QVBoxLayout) -> None:
    header_layout.setContentsMargins(CFG.MARGIN_SM, CFG.SPACING_XS, CFG.MARGIN_SM, CFG.SPACING_XS)
    header_layout.setSpacing(CFG.SPACING_SM)
    intro_layout.setSpacing(CFG.SPACING_XS)


def build_inventory_header_badge_widget(*badges: QLabel) -> QWidget:
    container = QWidget()
    layout = QGridLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setHorizontalSpacing(CFG.SPACING_XS)
    layout.setVerticalSpacing(CFG.SPACING_XS)
    for index, badge in enumerate(badges):
        layout.addWidget(badge, index // 3, index % 3, 1, 1, Qt.AlignRight)
    return container


__all__ = ["build_inventory_header_badge_widget", "configure_inventory_header_layout"]
