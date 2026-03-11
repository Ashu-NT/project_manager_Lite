from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ui.dashboard.styles import dashboard_badge_style, dashboard_meta_chip_style, dashboard_summary_style
from ui.dashboard.workqueue_button import DashboardQueueButton
from ui.styles.ui_config import UIConfig as CFG


class DashboardTopBarMixin:
    def _build_dashboard_top_bar(self) -> QWidget:
        top_bar = QFrame()
        top_bar.setObjectName("dashboardTopBar")
        top_bar.setStyleSheet(
            dashboard_summary_style()
            + f"""
            QFrame#dashboardTopBar {{
                border-radius: 18px;
                border: 1px solid {CFG.COLOR_BORDER};
            }}
            QLabel#dashboardTopTitle {{
                color: {CFG.COLOR_TEXT_PRIMARY};
                font-size: 18pt;
                font-weight: 800;
            }}
            QLabel#dashboardTopSubtitle {{
                color: {CFG.COLOR_TEXT_SECONDARY};
                font-size: 9pt;
            }}
            QLabel#dashboardTopEyebrow {{
                color: {CFG.COLOR_TEXT_MUTED};
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QFrame#dashboardTopStatus {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 14px;
            }}
            QLabel#dashboardTopStatusCopy {{
                color: {CFG.COLOR_TEXT_SECONDARY};
                font-size: 8.5pt;
            }}
            """
        )

        root = QHBoxLayout(top_bar)
        root.setContentsMargins(CFG.SPACING_MD, CFG.SPACING_SM, CFG.SPACING_MD, CFG.SPACING_SM)
        root.setSpacing(CFG.SPACING_SM)

        overview = QVBoxLayout()
        overview.setSpacing(CFG.SPACING_XS)

        title_row = QHBoxLayout()
        title_row.setSpacing(CFG.SPACING_SM)
        self.project_label_prefix = QLabel("PROJECT OVERVIEW")
        self.project_label_prefix.setObjectName("dashboardTopEyebrow")
        title_copy = QVBoxLayout()
        title_copy.setSpacing(0)
        title_copy.addWidget(self.project_label_prefix)
        self.project_title_lbl = QLabel("Select a project to see schedule and cost health.")
        self.project_title_lbl.setObjectName("dashboardTopTitle")
        self.project_title_lbl.setWordWrap(True)
        title_copy.addWidget(self.project_title_lbl)
        self.project_subtitle_lbl = QLabel("")
        self.project_subtitle_lbl.setObjectName("dashboardTopSubtitle")
        self.project_subtitle_lbl.setWordWrap(True)
        self.project_subtitle_lbl.hide()
        title_copy.addWidget(self.project_subtitle_lbl)
        title_row.addLayout(title_copy, 1)
        self.project_mode_badge = QLabel("Project View")
        self.project_mode_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        title_row.addWidget(self.project_mode_badge, 0, Qt.AlignTop)
        overview.addLayout(title_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(CFG.SPACING_XS)
        chip_style = dashboard_meta_chip_style()
        self.project_meta_scope = QLabel("")
        self.project_meta_start = QLabel("")
        self.project_meta_end = QLabel("")
        self.project_meta_duration = QLabel("")
        for label in (
            self.project_meta_scope,
            self.project_meta_start,
            self.project_meta_end,
            self.project_meta_duration,
        ):
            label.setStyleSheet(chip_style)
            label.hide()
            meta_row.addWidget(label)
        meta_row.addStretch()
        overview.addLayout(meta_row)
        root.addLayout(overview, 1)

        status_card = QFrame()
        status_card.setObjectName("dashboardTopStatus")
        status_layout = QVBoxLayout(status_card)
        status_layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        status_layout.setSpacing(CFG.SPACING_XS)
        self.dashboard_mode_badge = QLabel("Project View")
        self.dashboard_mode_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.dashboard_scope_hint = QLabel("4 panels active")
        self.dashboard_scope_hint.setObjectName("dashboardTopStatusCopy")
        status_layout.addWidget(self.dashboard_mode_badge)
        status_layout.addWidget(self.dashboard_scope_hint)
        root.addWidget(status_card)

        queue_row = QHBoxLayout()
        queue_row.setSpacing(CFG.SPACING_SM)
        self.btn_open_conflicts = DashboardQueueButton("Conflicts", active_variant="danger")
        self.btn_open_alerts = DashboardQueueButton("Alerts", active_variant="warning")
        self.btn_open_upcoming = DashboardQueueButton("Upcoming", active_variant="info")
        for btn in (self.btn_open_conflicts, self.btn_open_alerts, self.btn_open_upcoming):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            queue_row.addWidget(btn)
        root.addLayout(queue_row)

        self.btn_open_conflicts.set_variants(active="danger", inactive="success")
        self.btn_open_alerts.set_variants(active="warning", inactive="success")
        self.btn_open_upcoming.set_variants(active="info", inactive="neutral")
        return top_bar


__all__ = ["DashboardTopBarMixin"]
