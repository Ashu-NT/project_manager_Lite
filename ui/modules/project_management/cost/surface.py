from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from ui.modules.project_management.dashboard.styles import dashboard_action_button_style, dashboard_badge_style, dashboard_meta_chip_style
from src.ui.shared.widgets.guards import apply_permission_hint
from src.ui.shared.formatting.ui_config import UIConfig as CFG


def _kpi_card(title: str, value: str = "-") -> tuple[QFrame, QLabel]:
    card = QFrame()
    card.setStyleSheet(CFG.PROJECT_SUMMARY_BOX_STYLE)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
    layout.setSpacing(2)
    lbl_title = QLabel(title)
    lbl_title.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
    lbl_value = QLabel(value)
    lbl_value.setStyleSheet(CFG.DASHBOARD_KPI_VALUE_TEMPLATE.format(color=CFG.COLOR_ACCENT))
    layout.addWidget(lbl_title)
    layout.addWidget(lbl_value)
    return card, lbl_value


class CostSurfaceMixin:
    project_combo: QComboBox
    btn_reload_projects: QPushButton
    btn_new: QPushButton
    btn_edit: QPushButton
    btn_delete: QPushButton
    btn_refresh_costs: QPushButton
    _can_create_cost: bool
    _can_edit_cost: bool
    _can_delete_cost: bool
    _current_project: object | None

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        self.cost_header_card = header
        header.setObjectName("costHeaderCard")
        header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        header.setStyleSheet(
            f"QWidget#costHeaderCard {{ background-color: {CFG.COLOR_BG_SURFACE}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        header_layout.setAlignment(Qt.AlignTop)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("COSTS")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        title = QLabel("Cost Control")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Track budget health, labor usage, and detailed project costs.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(720)
        for widget in (eyebrow, title, subtitle):
            intro.addWidget(widget)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.cost_project_badge = QLabel("No Project")
        self.cost_project_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.cost_count_badge = QLabel("0 items")
        self.cost_count_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Action Enabled" if any((self._can_create_cost, self._can_edit_cost, self._can_delete_cost)) else "Read Only"
        self.cost_access_badge = QLabel(access_label)
        self.cost_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.cost_project_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.cost_count_badge, 0, Qt.AlignRight)
        status_layout.addWidget(self.cost_access_badge, 0, Qt.AlignRight)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        root.addWidget(header)

        controls = QWidget()
        self.cost_controls_card = controls
        controls.setObjectName("costControlSurface")
        controls.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        controls.setStyleSheet(
            f"QWidget#costControlSurface {{ background-color: {CFG.COLOR_BG_SURFACE_ALT}; border: 1px solid {CFG.COLOR_BORDER}; border-radius: 12px; }}"
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)
        top = QHBoxLayout()
        top.addWidget(QLabel("Project"))
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        self.btn_reload_projects.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_reload_projects.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_new = QPushButton(CFG.NEW_COST_ITEM_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_refresh_costs = QPushButton(CFG.REFRESH_COSTS_LABEL)
        for btn in (self.btn_reload_projects, self.btn_new, self.btn_edit, self.btn_delete, self.btn_refresh_costs):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_reload_projects.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_delete.setStyleSheet(dashboard_action_button_style("danger"))
        self.btn_refresh_costs.setStyleSheet(dashboard_action_button_style("secondary"))
        top.addWidget(self.project_combo, 1)
        top.addWidget(self.btn_reload_projects)
        top.addSpacing(CFG.SPACING_MD)
        top.addWidget(self.btn_new)
        top.addWidget(self.btn_edit)
        top.addWidget(self.btn_delete)
        top.addStretch()
        top.addWidget(self.btn_refresh_costs)
        controls_layout.addLayout(top)
        root.addWidget(controls)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(CFG.SPACING_SM)
        for title_text, attr in (
            ("Budget", "lbl_kpi_budget"),
            ("Planned", "lbl_kpi_planned"),
            ("Committed", "lbl_kpi_committed"),
            ("Actual", "lbl_kpi_actual"),
            ("Available", "lbl_kpi_remaining"),
        ):
            card, label = _kpi_card(title_text)
            setattr(self, attr, label)
            kpi_row.addWidget(card)
        root.addLayout(kpi_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        root.addWidget(splitter, 1)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(CFG.SPACING_SM)
        left_layout.addWidget(self._build_cost_items_group())
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(CFG.SPACING_SM)
        right_layout.addWidget(self._build_labor_group(), 1)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([820, 420])

        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_costs.clicked.connect(self.reload_costs)
        self.btn_new.clicked.connect(self.create_cost_item)
        self.btn_edit.clicked.connect(self.edit_cost_item)
        self.btn_delete.clicked.connect(self.delete_cost_item)
        self.filter_text.textChanged.connect(self._schedule_cost_filter_refresh)
        self.filter_type_combo.currentIndexChanged.connect(self._schedule_cost_filter_refresh)
        self.filter_task_combo.currentIndexChanged.connect(self._schedule_cost_filter_refresh)
        self.btn_clear_filters.clicked.connect(self._clear_cost_filters)
        self.btn_clear_filters.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_labor_details.clicked.connect(self.show_labor_details)
        self.btn_labor_details.setStyleSheet(dashboard_action_button_style("secondary"))
        self.tbl_labor_summary.itemSelectionChanged.connect(self._on_labor_table_selected)
        self.table.selectionModel().selectionChanged.connect(self._sync_cost_actions)

        for btn, allowed in ((self.btn_new, self._can_create_cost), (self.btn_edit, self._can_edit_cost), (self.btn_delete, self._can_delete_cost)):
            apply_permission_hint(btn, allowed=allowed, missing_permission="cost.manage or approval.request")
        self._sync_cost_actions()

    def _sync_cost_actions(self, *_args) -> None:
        has_project = self._current_project_id() is not None
        has_selected_cost = self._get_selected_cost() is not None
        self.btn_new.setEnabled(self._can_create_cost and has_project)
        self.btn_edit.setEnabled(self._can_edit_cost and has_project and has_selected_cost)
        self.btn_delete.setEnabled(self._can_delete_cost and has_project and has_selected_cost)

    def _update_cost_header_badges(self, visible_count: int, total_count: int) -> None:
        project_name = getattr(self._current_project, "name", "") or "No Project"
        self.cost_project_badge.setText(project_name)
        self.cost_count_badge.setText(f"{visible_count} of {total_count} items" if total_count and visible_count != total_count else f"{total_count} items")
