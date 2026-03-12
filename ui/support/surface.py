from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.dashboard.styles import dashboard_action_button_style, dashboard_badge_style, dashboard_meta_chip_style
from ui.styles.ui_config import UIConfig as CFG


def build_support_header(tab, root: QVBoxLayout) -> None:
    header = QWidget()
    tab.support_header_card = header
    header.setObjectName("supportHeaderCard")
    header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
    header.setStyleSheet(
        f"QWidget#supportHeaderCard {{ background-color: {CFG.COLOR_BG_SURFACE}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
    )
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
    header_layout.setSpacing(CFG.SPACING_MD)
    header_layout.setAlignment(Qt.AlignTop)
    intro = QVBoxLayout()
    intro.setSpacing(CFG.SPACING_XS)
    for widget in (
        QLabel("SUPPORT"),
        QLabel("Support & Updates"),
        QLabel("Operational tooling for release checks, diagnostics export, and incident tracing."),
    ):
        intro.addWidget(widget)
    intro.itemAt(0).widget().setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    intro.itemAt(1).widget().setStyleSheet(CFG.TITLE_LARGE_STYLE)
    intro.itemAt(2).widget().setStyleSheet(CFG.INFO_TEXT_STYLE)
    intro.itemAt(2).widget().setWordWrap(True)
    intro.itemAt(2).widget().setMaximumWidth(760)
    header_layout.addLayout(intro, 1)
    status_layout = QVBoxLayout()
    status_layout.setSpacing(CFG.SPACING_SM)
    tab.support_channel_badge = QLabel("Stable")
    tab.support_channel_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
    tab.support_policy_badge = QLabel("Manual Check")
    tab.support_policy_badge.setStyleSheet(dashboard_meta_chip_style())
    tab.support_trace_badge = QLabel("Trace Ready")
    tab.support_trace_badge.setStyleSheet(dashboard_meta_chip_style())
    for badge in (tab.support_channel_badge, tab.support_policy_badge, tab.support_trace_badge):
        status_layout.addWidget(badge, 0, Qt.AlignRight)
    status_layout.addStretch(1)
    header_layout.addLayout(status_layout)
    root.addWidget(header)


def style_support_button(button: QPushButton, variant: str) -> None:
    button.setFixedHeight(CFG.BUTTON_HEIGHT)
    button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
    button.setStyleSheet(dashboard_action_button_style(variant))


def update_support_header_badges(tab) -> None:
    tab.support_channel_badge.setText(tab.channel_combo.currentText().strip() or "Stable")
    tab.support_policy_badge.setText("Auto-check On" if tab.auto_check.isChecked() else "Manual Check")
    tab.support_trace_badge.setText("Trace Ready" if tab.incident_id_input.text().strip() else "Trace Pending")
