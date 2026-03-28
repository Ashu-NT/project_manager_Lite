from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QVBoxLayout

from ui.modules.project_management.dashboard.styles import dashboard_action_button_style
from ui.platform.admin.shared_header import build_admin_header
from ui.platform.shared.styles.ui_config import UIConfig as CFG


def build_support_header(tab, root: QVBoxLayout) -> None:
    tab.support_header_card = build_admin_header(
        tab,
        root,
        object_name="supportHeaderCard",
        eyebrow_text="SUPPORT",
        title_text="Support & Updates",
        subtitle_text="Operational tooling for release checks, diagnostics export, and incident tracing.",
        badge_specs=(
            ("support_channel_badge", "Stable", "accent"),
            ("support_policy_badge", "Manual Check", "meta"),
            ("support_trace_badge", "Trace Ready", "meta"),
        ),
    )


def style_support_button(button: QPushButton, variant: str) -> None:
    button.setFixedHeight(CFG.BUTTON_HEIGHT)
    button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
    button.setStyleSheet(dashboard_action_button_style(variant))


def update_support_header_badges(tab) -> None:
    tab.support_channel_badge.setText(tab.channel_combo.currentText().strip() or "Stable")
    tab.support_policy_badge.setText("Auto-check On" if tab.auto_check.isChecked() else "Manual Check")
    tab.support_trace_badge.setText("Trace Ready" if tab.incident_id_input.text().strip() else "Trace Pending")
