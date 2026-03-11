from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.dashboard.styles import dashboard_action_button_style, dashboard_summary_style
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
            QFrame#dashboardControlCard {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 14px;
            }}
            QLabel#dashboardEyebrow {{
                color: {CFG.COLOR_TEXT_MUTED};
                font-size: 9pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel#dashboardHeading {{
                color: {CFG.COLOR_TEXT_PRIMARY};
                font-size: 18pt;
                font-weight: 800;
            }}
            QLabel#dashboardSubheading {{
                color: {CFG.COLOR_TEXT_SECONDARY};
                font-size: 9.5pt;
            }}
            QLabel#dashboardControlTitle {{
                color: {CFG.COLOR_TEXT_MUTED};
                font-size: 8.5pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            """
        )

        root = QVBoxLayout(top_bar)
        root.setContentsMargins(CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD)
        root.setSpacing(CFG.SPACING_MD)

        header_row = QHBoxLayout()
        header_row.setSpacing(CFG.SPACING_MD)

        header_copy = QVBoxLayout()
        header_copy.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("DELIVERY CONTROL")
        eyebrow.setObjectName("dashboardEyebrow")
        heading = QLabel("Dashboard Control Center")
        heading.setObjectName("dashboardHeading")
        subheading = QLabel(
            "Switch between project and portfolio views, tune visible panels, "
            "and keep execution pressure in one place."
        )
        subheading.setObjectName("dashboardSubheading")
        subheading.setWordWrap(True)
        header_copy.addWidget(eyebrow)
        header_copy.addWidget(heading)
        header_copy.addWidget(subheading)
        header_row.addLayout(header_copy, 1)

        queue_row = QHBoxLayout()
        queue_row.setSpacing(CFG.SPACING_SM)
        self.btn_open_conflicts = DashboardQueueButton("Conflicts", active_variant="danger")
        self.btn_open_alerts = DashboardQueueButton("Alerts", active_variant="warning")
        self.btn_open_upcoming = DashboardQueueButton("Upcoming", active_variant="info")
        for btn in (self.btn_open_conflicts, self.btn_open_alerts, self.btn_open_upcoming):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            queue_row.addWidget(btn)
        header_row.addLayout(queue_row)
        root.addLayout(header_row)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(CFG.SPACING_SM)
        controls_row.addWidget(self._control_card("View", self.project_combo, self.btn_reload_projects), 3)
        controls_row.addWidget(self._control_card("Baseline", self.baseline_combo, self.btn_create_baseline, self.btn_delete_baseline), 3)
        controls_row.addWidget(self._control_card("Actions", self.btn_refresh_dashboard, self.btn_customize_dashboard), 2)
        root.addLayout(controls_row)

        self.btn_refresh_dashboard.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_reload_projects.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_customize_dashboard.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_create_baseline.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_delete_baseline.setStyleSheet(dashboard_action_button_style("danger"))
        self.btn_open_conflicts.set_variants(active="danger", inactive="success")
        self.btn_open_alerts.set_variants(active="warning", inactive="success")
        self.btn_open_upcoming.set_variants(active="info", inactive="neutral")
        return top_bar

    def _control_card(self, title: str, *widgets: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("dashboardControlCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        layout.setSpacing(CFG.SPACING_SM)
        title_label = QLabel(title.upper())
        title_label.setObjectName("dashboardControlTitle")
        layout.addWidget(title_label)

        row = QHBoxLayout()
        row.setSpacing(CFG.SPACING_SM)
        for widget in widgets:
            if isinstance(widget, QPushButton):
                widget.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
                widget.setFixedHeight(CFG.BUTTON_HEIGHT)
            row.addWidget(widget)
        layout.addLayout(row)
        return card


__all__ = ["DashboardTopBarMixin"]
