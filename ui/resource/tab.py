from __future__ import annotations

from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.services.auth import UserSessionContext
from core.services.resource import ResourceService
from ui.resource.actions import ResourceActionsMixin
from ui.resource.flow import ResourceFlowMixin
from ui.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.resource.models import ResourceTableModel
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class ResourceTab(ResourceFlowMixin, ResourceActionsMixin, QWidget):
    """Resource tab coordinator: UI wiring + delegates actions/flow to mixins."""

    def __init__(
        self,
        resource_service: ResourceService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._resource_service: ResourceService = resource_service
        self._user_session = user_session
        self._can_manage_resources = has_permission(self._user_session, "resource.manage")

        self._setup_ui()
        self.reload_resources()
        self._sync_actions()
        domain_events.resources_changed.connect(self._on_resources_changed)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )

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

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_reload_resources)
        layout.addLayout(toolbar)

        self.table = QTableView()
        self.model = ResourceTableModel()
        self.table.setModel(self.model)
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
        hh.resizeSection(1, 180)
        layout.addWidget(self.table)

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

        apply_permission_hint(
            self.btn_new,
            allowed=self._can_manage_resources,
            missing_permission="resource.manage",
        )
        apply_permission_hint(
            self.btn_edit,
            allowed=self._can_manage_resources,
            missing_permission="resource.manage",
        )
        apply_permission_hint(
            self.btn_delete,
            allowed=self._can_manage_resources,
            missing_permission="resource.manage",
        )
        apply_permission_hint(
            self.btn_toggle_active,
            allowed=self._can_manage_resources,
            missing_permission="resource.manage",
        )
        self._sync_actions()

    def _on_resources_changed(self, _resource_id: str) -> None:
        self.reload_resources()

    def _sync_actions(self, *_args) -> None:
        has_row = self._get_selected_resource() is not None
        self.btn_new.setEnabled(self._can_manage_resources)
        self.btn_edit.setEnabled(self._can_manage_resources and has_row)
        self.btn_delete.setEnabled(self._can_manage_resources and has_row)
        self.btn_toggle_active.setEnabled(self._can_manage_resources and has_row)
