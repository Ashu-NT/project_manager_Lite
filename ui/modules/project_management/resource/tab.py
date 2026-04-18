from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.platform.notifications.domain_events import domain_events
from core.modules.project_management.domain.resource import Resource
from src.core.platform.auth import UserSessionContext
from src.core.platform.org import EmployeeService
from core.modules.project_management.services.resource import ResourceService
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style, dashboard_badge_style, dashboard_meta_chip_style
from ui.modules.project_management.resource.actions import ResourceActionsMixin
from ui.modules.project_management.resource.employee_context import build_employee_context_map
from ui.modules.project_management.resource.filtering import ResourceFiltersMixin
from ui.modules.project_management.resource.flow import ResourceFlowMixin
from ui.modules.project_management.shared.domain_event_filters import should_refresh_resource_context
from ui.platform.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.modules.project_management.resource.models import ResourceTableModel
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class ResourceTab(ResourceFlowMixin, ResourceFiltersMixin, ResourceActionsMixin, QWidget):
    def __init__(
        self,
        resource_service: ResourceService,
        employee_service: EmployeeService | None = None,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._resource_service: ResourceService = resource_service
        self._employee_service: EmployeeService | None = employee_service
        self._user_session = user_session
        self._can_manage_resources = has_permission(self._user_session, "resource.manage")
        self._all_resources: list[Resource] = []

        self._setup_ui()
        self.reload_resources()
        self._sync_actions()
        domain_events.resources_changed.connect(self.reload_resources)
        domain_events.domain_changed.connect(self._on_domain_change)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        header = QWidget()
        self.resource_header_card = header
        header.setObjectName("resourceHeaderCard")
        header.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        header.setStyleSheet(
            f"""
            QWidget#resourceHeaderCard {{
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
        eyebrow = QLabel("RESOURCES")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Resource Pool")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel("Manage team capacity, cost categories, and resource availability from one workspace.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        subtitle.setMaximumWidth(720)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.resource_scope_badge = QLabel("All Resources")
        self.resource_scope_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.resource_count_badge = QLabel("0 visible")
        self.resource_count_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_resources else "Read Only"
        self.resource_access_badge = QLabel(access_label)
        self.resource_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.resource_scope_badge, 0)
        status_layout.addWidget(self.resource_count_badge, 0)
        status_layout.addWidget(self.resource_access_badge, 0)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        self.resource_controls_card = controls
        controls.setObjectName("resourceControlSurface")
        controls.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        controls.setStyleSheet(
            f"""
            QWidget#resourceControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE_ALT};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)

        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_RESOURCE_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_toggle_active = QPushButton(CFG.TOGGLE_ACTIVE_LABEL)
        self.btn_reload_resources = QPushButton(CFG.REFRESH_RESOURCES_LABEL)

        for btn in (
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_toggle_active,
            self.btn_reload_resources,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_delete.setStyleSheet(dashboard_action_button_style("danger"))
        self.btn_toggle_active.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_reload_resources.setStyleSheet(dashboard_action_button_style("secondary"))

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_reload_resources)
        controls_layout.addLayout(toolbar)
        self._build_resource_filters(controls_layout)
        self.btn_clear_resource_filters.setStyleSheet(dashboard_action_button_style("secondary"))
        layout.addWidget(controls)

        self.table = QTableView()
        self.model = ResourceTableModel()
        self.table.setModel(self.model)
        self.table.setSizePolicy(CFG.EXPAND_BOTH)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        style_table(self.table)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(False)
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.Interactive)
        hh.setSectionResizeMode(8, QHeaderView.Interactive)
        hh.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        hh.resizeSection(1, 180)
        hh.resizeSection(7, 220)
        hh.resizeSection(8, 180)
        layout.addWidget(self.table, 1)

        self.btn_reload_resources.clicked.connect(self.reload_resources)
        self.btn_new.clicked.connect(
            make_guarded_slot(self, title="Resources", callback=self.create_resource)
        )
        self.btn_edit.clicked.connect(
            make_guarded_slot(self, title="Resources", callback=self.edit_resource)
        )
        self.btn_delete.clicked.connect(
            make_guarded_slot(self, title="Resources", callback=self.delete_resource)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Resources", callback=self.toggle_active)
        )
        self.table.selectionModel().selectionChanged.connect(self._sync_actions)

        for button in (self.btn_new, self.btn_edit, self.btn_delete, self.btn_toggle_active):
            apply_permission_hint(button, allowed=self._can_manage_resources, missing_permission="resource.manage")
        self._sync_actions()

    def reload_resources(self, *_args) -> None:
        selected = self._get_selected_resource()
        selected_id = selected.id if selected else None
        try:
            self._employee_context_by_id = build_employee_context_map(self._employee_service)
        except Exception:
            self._employee_context_by_id = {}
        self.model.set_employee_contexts(self._employee_context_by_id)
        self._all_resources = self._resource_service.list_resources()
        self._render_resource_rows(preferred_resource_id=selected_id)

    def _on_domain_change(self, event) -> None:
        if should_refresh_resource_context(event):
            self.reload_resources()

    def _sync_actions(self, *_args) -> None:
        has_row = self._get_selected_resource() is not None
        self.btn_new.setEnabled(self._can_manage_resources)
        self.btn_edit.setEnabled(self._can_manage_resources and has_row)
        self.btn_delete.setEnabled(self._can_manage_resources and has_row)
        self.btn_toggle_active.setEnabled(self._can_manage_resources and has_row)

    def _update_resource_header_badges(self, visible_resources: list[Resource]) -> None:
        active_mode = str(self.resource_active_filter.currentData() or "").strip()
        category = str(self.resource_category_filter.currentText() or "").strip()
        scope_parts: list[str] = []
        if active_mode == "active":
            scope_parts.append("Active")
        elif active_mode == "inactive":
            scope_parts.append("Inactive")
        if self.resource_category_filter.currentIndex() > 0 and category:
            scope_parts.append(category)
        self.resource_scope_badge.setText(" | ".join(scope_parts) or "All Resources")
        self.resource_count_badge.setText(f"{len(visible_resources)} visible")
