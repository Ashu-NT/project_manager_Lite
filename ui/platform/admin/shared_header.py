from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.modules.project_management.dashboard.styles import dashboard_badge_style, dashboard_meta_chip_style
from ui.platform.shared.styles.ui_config import UIConfig as CFG


BadgeSpec = tuple[str, str, str]


def build_admin_header(
    target: object,
    root: QVBoxLayout,
    *,
    object_name: str,
    eyebrow_text: str,
    title_text: str,
    subtitle_text: str,
    badge_specs: Sequence[BadgeSpec],
    subtitle_max_width: int = 760,
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
    header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
    header_layout.setSpacing(CFG.SPACING_MD)
    header_layout.setAlignment(Qt.AlignTop)

    intro = QVBoxLayout()
    intro.setSpacing(CFG.SPACING_XS)
    eyebrow = QLabel(eyebrow_text)
    eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    title = QLabel(title_text)
    title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
    subtitle = QLabel(subtitle_text)
    subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
    subtitle.setWordWrap(True)
    subtitle.setMaximumWidth(subtitle_max_width)
    intro.addWidget(eyebrow)
    intro.addWidget(title)
    intro.addWidget(subtitle)
    header_layout.addLayout(intro, 3)

    badges_host = QHBoxLayout()
    badges_host.setSpacing(CFG.SPACING_SM)
    badges_host.setAlignment(Qt.AlignTop | Qt.AlignRight)

    split_index = max(1, (len(badge_specs) + 1) // 2)
    for column_specs in (badge_specs[:split_index], badge_specs[split_index:]):
        if not column_specs:
            continue
        column_layout = QVBoxLayout()
        column_layout.setSpacing(CFG.SPACING_XS)
        column_layout.setAlignment(Qt.AlignTop | Qt.AlignRight)
        for attr_name, text, badge_kind in column_specs:
            badge = QLabel(text)
            badge.setStyleSheet(_badge_style(badge_kind))
            setattr(target, attr_name, badge)
            column_layout.addWidget(badge, 0, Qt.AlignRight)
        column_layout.addStretch(1)
        badges_host.addLayout(column_layout, 1)
    header_layout.addLayout(badges_host, 2)

    root.addWidget(header)
    return header


def _badge_style(badge_kind: str) -> str:
    if badge_kind == "accent":
        return dashboard_badge_style(CFG.COLOR_ACCENT)
    return dashboard_meta_chip_style()


__all__ = ["build_admin_header"]
