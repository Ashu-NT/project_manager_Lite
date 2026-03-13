from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_badge_style,
    dashboard_summary_style,
)
from ui.platform.shared.styles.ui_config import UIConfig as CFG


PANEL_CATALOG: dict[str, tuple[str, str, str]] = {
    "kpi": ("KPI Cards", "Snap summary", "Fast health signals for scope, schedule, and cost."),
    "milestones": ("Milestone Health", "Project only", "Upcoming checkpoints with due-soon and late visibility."),
    "watchlist": ("Critical Path Watchlist", "Project only", "Critical or tight-float tasks that need active control."),
    "register": ("Risk / Issue / Change Summary", "Project only", "Urgent register counts and action-heavy items."),
    "evm": ("EVM Analysis", "Project only", "Earned value metrics for cost and schedule control."),
    "portfolio": ("Portfolio Ranking", "Portfolio only", "Cross-project ranking with at-risk visibility."),
    "burndown": ("Status Trend", "Chart", "Trend view for remaining work or portfolio status rollup."),
    "resource": ("Resource Capacity", "Chart", "Utilization and over-allocation pressure by resource."),
}

PROJECT_PANELS: tuple[str, ...] = ("kpi", "milestones", "watchlist", "register", "resource", "evm", "burndown")
PORTFOLIO_PANELS: tuple[str, ...] = ("kpi", "portfolio", "burndown", "resource")


class DashboardLayoutDialog(QDialog):
    def __init__(
        self,
        parent,
        *,
        current_layout: dict[str, object] | None = None,
        portfolio_mode: bool = False,
    ) -> None:
        super().__init__(parent)
        self._layout = dict(current_layout or {})
        self._portfolio_mode = bool(portfolio_mode)
        self._panel_checks: dict[str, QCheckBox] = {}
        self.resize(920, 600)
        self.setWindowTitle("Customize Dashboard")
        self._setup_ui()
        self._load_state()

    @property
    def _mode_key(self) -> str:
        return "portfolio" if self._portfolio_mode else "project"

    def _available_panels(self) -> tuple[str, ...]:
        return PORTFOLIO_PANELS if self._portfolio_mode else PROJECT_PANELS

    def _mode_layout(self) -> dict[str, object]:
        mode_layout = self._layout.get(self._mode_key)
        if isinstance(mode_layout, dict):
            return dict(mode_layout)
        defaults = list(self._available_panels())
        return {
            "visible_panels": defaults,
            "panel_order": defaults,
        }

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        self._apply_style()

        content = QHBoxLayout()
        content.setSpacing(CFG.SPACING_MD)
        root.addLayout(content, 1)

        main_col = QVBoxLayout()
        main_col.setSpacing(CFG.SPACING_MD)
        side_col = QVBoxLayout()
        side_col.setSpacing(CFG.SPACING_MD)
        content.addLayout(main_col, 3)
        content.addLayout(side_col, 2)

        intro_card = self._card()
        intro_layout = QVBoxLayout(intro_card)
        intro_layout.setContentsMargins(CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD)
        intro_layout.setSpacing(CFG.SPACING_SM)
        eyebrow = QLabel("DASHBOARD LAYOUT")
        eyebrow.setStyleSheet(CFG.DASHBOARD_PROJECT_LABEL_STYLE)
        heading = QLabel("Choose the panels worth the screen")
        heading.setStyleSheet("font-size: 15pt; font-weight: 800;")
        self.mode_badge = QLabel("")
        self.mode_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        note = QLabel(
            "The overview header always stays pinned. Below it, keep the working surface to 2-4 panels "
            "so the dashboard stays readable on a 14-inch laptop."
        )
        note.setWordWrap(True)
        note.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.selection_status = QLabel("")
        self.selection_status.setWordWrap(True)
        self.selection_status.setStyleSheet(CFG.INFO_TEXT_STYLE)
        intro_layout.addWidget(eyebrow)
        intro_layout.addWidget(heading)
        intro_layout.addWidget(self.mode_badge, 0, Qt.AlignLeft)
        intro_layout.addWidget(note)
        intro_layout.addWidget(self.selection_status)
        main_col.addWidget(intro_card)

        options_card = self._card()
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD)
        options_layout.setSpacing(CFG.SPACING_SM)
        options_layout.addWidget(QLabel("Available Panels"))
        for panel_id in self._available_panels():
            options_layout.addWidget(self._build_panel_option(panel_id))
        main_col.addWidget(options_card)

        order_card = self._card()
        order_layout = QVBoxLayout(order_card)
        order_layout.setContentsMargins(CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD)
        order_layout.setSpacing(CFG.SPACING_SM)
        order_layout.addWidget(QLabel("Display Priority"))
        order_hint = QLabel("Drag panels to control which ones appear first on the dashboard surface.")
        order_hint.setWordWrap(True)
        order_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        order_layout.addWidget(order_hint)
        self.panel_order_list = QListWidget()
        self.panel_order_list.setDragDropMode(QListWidget.InternalMove)
        self.panel_order_list.setAlternatingRowColors(True)
        self.panel_order_list.setMinimumHeight(210)
        order_layout.addWidget(self.panel_order_list)
        side_col.addWidget(order_card)

        preset_card = self._card()
        preset_layout = QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD, CFG.SPACING_MD)
        preset_layout.setSpacing(CFG.SPACING_SM)
        preset_layout.addWidget(QLabel("Screen Profiles"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItem("Balanced (Recommended)", userData="balanced")
        self.preset_combo.addItem("Executive", userData="executive")
        self.preset_combo.addItem("Delivery Focus", userData="delivery")
        self.preset_combo.addItem("Lean", userData="lean")
        preset_layout.addWidget(self.preset_combo)
        preset_copy = QLabel(
            "Balanced keeps four panels. The other profiles trim the screen to the most decision-heavy views."
        )
        preset_copy.setWordWrap(True)
        preset_copy.setStyleSheet(CFG.INFO_TEXT_STYLE)
        preset_layout.addWidget(preset_copy)
        self.view_hint = QLabel("")
        self.view_hint.setWordWrap(True)
        self.view_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        preset_layout.addWidget(self.view_hint)
        side_col.addWidget(preset_card)
        side_col.addStretch()

        buttons = QHBoxLayout()
        self.btn_apply_preset = QPushButton("Apply Profile")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save Layout")
        self.btn_apply_preset.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_cancel.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_save.setStyleSheet(dashboard_action_button_style("primary"))
        buttons.addWidget(self.btn_apply_preset)
        buttons.addStretch()
        buttons.addWidget(self.btn_cancel)
        buttons.addWidget(self.btn_save)
        root.addLayout(buttons)

        self.btn_apply_preset.clicked.connect(self._apply_preset)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self.accept)
        for checkbox in self._panel_checks.values():
            checkbox.toggled.connect(self._sync_selection_state)

    def _apply_style(self) -> None:
        self.setStyleSheet(
            dashboard_summary_style()
            + f"""
            QFrame#dashboardLayoutCard {{
                border-radius: 16px;
            }}
            QFrame#dashboardPanelOption {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            QListWidget {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 10px;
            }}
            QLabel#dashboardPanelMeta {{
                color: {CFG.COLOR_TEXT_MUTED};
                font-size: 8.5pt;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QLabel#dashboardPanelCopy {{
                color: {CFG.COLOR_TEXT_SECONDARY};
                font-size: 9pt;
            }}
            """
        )

    def _card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("dashboardLayoutCard")
        return card

    def _build_panel_option(self, panel_id: str) -> QWidget:
        title, meta, description = PANEL_CATALOG[panel_id]
        card = QFrame()
        card.setObjectName("dashboardPanelOption")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM, CFG.SPACING_SM)
        layout.setSpacing(CFG.SPACING_XS)
        header = QHBoxLayout()
        header.setSpacing(CFG.SPACING_SM)
        checkbox = QCheckBox(title)
        self._panel_checks[panel_id] = checkbox
        meta_label = QLabel(meta.upper())
        meta_label.setObjectName("dashboardPanelMeta")
        header.addWidget(checkbox)
        header.addStretch()
        header.addWidget(meta_label)
        copy = QLabel(description)
        copy.setObjectName("dashboardPanelCopy")
        copy.setWordWrap(True)
        layout.addLayout(header)
        layout.addWidget(copy)
        return card

    def _load_state(self) -> None:
        mode_layout = self._mode_layout()
        visible = self._normalize_visible(mode_layout.get("visible_panels"))
        order = self._normalize_order(mode_layout.get("panel_order"), self._available_panels())
        for panel_id, checkbox in self._panel_checks.items():
            checkbox.setChecked(panel_id in visible)
        self._set_order_list(order)
        self._sync_mode_copy()
        self._sync_selection_state()

    def _sync_mode_copy(self) -> None:
        if self._portfolio_mode:
            self.mode_badge.setText("Portfolio View")
            self.view_hint.setText(
                "Portfolio view swaps project EVM for the portfolio ranking panel."
            )
            return
        self.mode_badge.setText("Project View")
        self.view_hint.setText("Project view adds milestone and critical-path control panels.")

    def _selected_panel_ids(self) -> list[str]:
        ordered = self._order_from_list(self.panel_order_list, self._available_panels())
        return [panel_id for panel_id in ordered if self._panel_checks[panel_id].isChecked()]

    def _sync_selection_state(self) -> None:
        count = len(self._selected_panel_ids())
        self.btn_save.setEnabled(2 <= count <= 4)
        if count < 2:
            text = "Select at least 2 panels so the dashboard keeps enough context."
        else:
            text = f"{count} panels selected for this view. The overview header stays pinned above them."
        self.selection_status.setText(text)

    def _apply_preset(self) -> None:
        panels = self._available_panels()
        analysis = "portfolio" if self._portfolio_mode else "evm"
        presets = {
            "balanced": list(panels if self._portfolio_mode else ("kpi", "milestones", "watchlist", "register")),
            "executive": [analysis, "kpi", "burndown"] if self._portfolio_mode else ["kpi", "milestones", "register"],
            "delivery": [analysis, "resource", "burndown"] if self._portfolio_mode else ["watchlist", "register", "resource", "evm"],
            "lean": ["kpi", "burndown"] if self._portfolio_mode else ["kpi", "register"],
        }
        order_presets = {
            "balanced": list(panels),
            "executive": [analysis, "kpi", "burndown", "resource"] if self._portfolio_mode else ["kpi", "milestones", "register", "watchlist", "resource", "evm", "burndown"],
            "delivery": [analysis, "resource", "burndown", "kpi"] if self._portfolio_mode else ["watchlist", "register", "resource", "burndown", "evm", "kpi", "milestones"],
            "lean": ["kpi", "burndown", analysis, "resource"] if self._portfolio_mode else ["kpi", "register", "milestones", "watchlist", "resource", "evm", "burndown"],
        }
        preset = str(self.preset_combo.currentData() or "balanced")
        selected = set(presets.get(preset, list(panels)))
        for panel_id, checkbox in self._panel_checks.items():
            checkbox.setChecked(panel_id in selected)
        self._set_order_list(order_presets.get(preset, list(panels)))
        self._sync_selection_state()

    @property
    def layout_payload(self) -> dict[str, object]:
        payload = {
            "project": dict(self._layout.get("project") or {}),
            "portfolio": dict(self._layout.get("portfolio") or {}),
        }
        payload[self._mode_key] = {
            "visible_panels": self._selected_panel_ids(),
            "panel_order": self._order_from_list(self.panel_order_list, self._available_panels()),
        }
        return payload

    def _normalize_visible(self, value: object) -> list[str]:
        selected: list[str] = []
        allowed = set(self._available_panels())
        if isinstance(value, (list, tuple)):
            for row in value:
                panel_id = str(row or "").strip().lower()
                if panel_id in allowed and panel_id not in selected:
                    selected.append(panel_id)
        if len(selected) < 2:
            for panel_id in self._available_panels():
                if panel_id not in selected:
                    selected.append(panel_id)
                if len(selected) >= 2:
                    break
        return selected[:4]

    @staticmethod
    def _normalize_order(value: object, defaults: tuple[str, ...]) -> list[str]:
        allowed = set(defaults)
        order: list[str] = []
        if isinstance(value, (list, tuple)):
            for row in value:
                token = str(row or "").strip().lower()
                if token in allowed and token not in order:
                    order.append(token)
        for token in defaults:
            if token not in order:
                order.append(token)
        return order

    def _set_order_list(self, order: list[str]) -> None:
        self.panel_order_list.clear()
        for panel_id in order:
            title = PANEL_CATALOG[panel_id][0]
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, panel_id)
            self.panel_order_list.addItem(item)

    @staticmethod
    def _order_from_list(list_widget: QListWidget, defaults: tuple[str, ...]) -> list[str]:
        order: list[str] = []
        for idx in range(list_widget.count()):
            item = list_widget.item(idx)
            token = str(item.data(Qt.UserRole) or "").strip().lower()
            if token and token not in order:
                order.append(token)
        for token in defaults:
            if token not in order:
                order.append(token)
        return order


__all__ = ["DashboardLayoutDialog"]
