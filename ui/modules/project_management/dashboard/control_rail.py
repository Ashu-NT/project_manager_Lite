from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.modules.project_management.dashboard.styles import dashboard_action_button_style, dashboard_summary_style
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class DashboardControlRailMixin:
    def _build_dashboard_control_sidebar(self) -> QWidget:
        self.dashboard_control_stack = QStackedWidget()
        self.dashboard_control_stack.addWidget(self._build_dashboard_control_panel())
        self.dashboard_control_stack.addWidget(self._build_dashboard_control_stub())
        self._set_dashboard_controls_collapsed(False)
        return self.dashboard_control_stack

    def _build_dashboard_control_panel(self) -> QWidget:
        rail = QFrame()
        rail.setObjectName("dashboardControlRail")
        rail.setStyleSheet(
            dashboard_summary_style()
            + f"""
            QFrame#dashboardControlRail {{
                border-radius: 18px;
            }}
            QFrame#dashboardControlSection {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 14px;
            }}
            QLabel#dashboardRailEyebrow {{
                color: {CFG.COLOR_TEXT_MUTED};
                font-size: 8.5pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel#dashboardRailTitle {{
                color: {CFG.COLOR_TEXT_PRIMARY};
                font-size: 11pt;
                font-weight: 800;
            }}
            QLabel#dashboardRailSectionTitle {{
                color: {CFG.COLOR_TEXT_MUTED};
                font-size: 8.5pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            """
        )

        layout = QVBoxLayout(rail)
        layout.setContentsMargins(CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD)
        layout.setSpacing(CFG.SPACING_SM)

        header = QHBoxLayout()
        header.setSpacing(CFG.SPACING_SM)
        title = QLabel("Controls")
        title.setObjectName("dashboardRailTitle")
        header.addWidget(title, 1)

        self.btn_hide_dashboard_controls = QPushButton("Collapse")
        self.btn_hide_dashboard_controls.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_hide_dashboard_controls.clicked.connect(lambda: self._set_dashboard_controls_collapsed(True))
        header.addWidget(self.btn_hide_dashboard_controls)
        layout.addLayout(header)

        layout.addWidget(
            self._dashboard_control_section(
                "View",
                self.project_combo,
                self.btn_reload_projects,
            )
        )
        layout.addWidget(
            self._dashboard_control_section(
                "Baseline",
                self.baseline_combo,
                self.btn_create_baseline,
                self.btn_delete_baseline,
            )
        )
        layout.addWidget(
            self._dashboard_control_section(
                "Actions",
                self.btn_refresh_dashboard,
                self.btn_customize_dashboard,
            )
        )
        layout.addStretch()

        self.btn_refresh_dashboard.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_reload_projects.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_customize_dashboard.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_create_baseline.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_delete_baseline.setStyleSheet(dashboard_action_button_style("danger"))
        return rail

    def _build_dashboard_control_stub(self) -> QWidget:
        stub = QFrame()
        stub.setObjectName("dashboardControlStub")
        stub.setStyleSheet(
            dashboard_summary_style()
            + f"""
            QFrame#dashboardControlStub {{
                border-radius: 16px;
            }}
            QLabel#dashboardStubLabel {{
                color: {CFG.COLOR_TEXT_MUTED};
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            """
        )
        layout = QVBoxLayout(stub)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        layout.setSpacing(CFG.SPACING_SM)
        label = QLabel("CONTROLS")
        label.setObjectName("dashboardStubLabel")
        label.setAlignment(CFG.ALIGN_CENTER)
        self.btn_show_dashboard_controls = QPushButton("Open")
        self.btn_show_dashboard_controls.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_show_dashboard_controls.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        self.btn_show_dashboard_controls.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_show_dashboard_controls.setMinimumWidth(88)
        self.btn_show_dashboard_controls.clicked.connect(lambda: self._set_dashboard_controls_collapsed(False))
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(self.btn_show_dashboard_controls)
        layout.addStretch()
        return stub

    def _dashboard_control_section(self, title: str, *widgets: QWidget) -> QWidget:
        card = QFrame()
        card.setObjectName("dashboardControlSection")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        layout.setSpacing(CFG.SPACING_SM)
        title_label = QLabel(title.upper())
        title_label.setObjectName("dashboardRailSectionTitle")
        layout.addWidget(title_label)
        for widget in widgets:
            if isinstance(widget, QPushButton):
                widget.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
                widget.setFixedHeight(CFG.BUTTON_HEIGHT)
            if isinstance(widget, QComboBox):
                widget.setSizePolicy(CFG.INPUT_POLICY)
                widget.setFixedHeight(CFG.INPUT_HEIGHT)
            layout.addWidget(widget)
        return card

    def _set_dashboard_controls_collapsed(self, collapsed: bool) -> None:
        if not hasattr(self, "dashboard_control_stack"):
            return
        self._dashboard_controls_collapsed = bool(collapsed)
        self.dashboard_control_stack.setCurrentIndex(1 if collapsed else 0)
        self.dashboard_control_stack.setFixedWidth(128 if collapsed else 290)
        if hasattr(self, "_sync_dashboard_panel_visibility"):
            self._sync_dashboard_panel_visibility()


__all__ = ["DashboardControlRailMixin"]
