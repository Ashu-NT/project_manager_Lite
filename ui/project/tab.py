from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.models import Project
from core.services.auth import UserSessionContext
from core.services.project import ProjectResourceService, ProjectService
from core.services.reporting import ReportingService
from core.services.resource import ResourceService
from core.services.task import TaskService
from ui.project.actions import ProjectActionsMixin
from ui.project.dialogs import ProjectEditDialog  # noqa: F401
from ui.project.filtering import ProjectFiltersMixin
from ui.project.models import ProjectTableModel
from ui.project.resource_panel import ProjectResourcePanelMixin
from ui.shared.guards import apply_permission_hint, has_permission, make_guarded_slot
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class ProjectTab(ProjectActionsMixin, ProjectFiltersMixin, ProjectResourcePanelMixin, QWidget):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        reporting_service: ReportingService,
        project_resource_service: ProjectResourceService,
        resource_service: ResourceService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._reporting_service: ReportingService = reporting_service
        self._project_resource_service: ProjectResourceService = project_resource_service
        self._resource_service: ResourceService = resource_service
        self._user_session = user_session
        self._can_manage_projects = has_permission(self._user_session, "project.manage")
        self._can_manage_project_resources = self._can_manage_projects
        self._all_projects: list[Project] = []

        self._setup_ui()
        self.reload_projects()
        self._sync_actions()
        domain_events.project_changed.connect(self._on_project_changed_event)
        domain_events.resources_changed.connect(self._on_resources_changed_event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_new = QPushButton(CFG.NEW_PROJECT_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_refresh = QPushButton(CFG.REFRESH_PROJECTS_LABEL)

        for btn in (
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_refresh,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_delete)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        layout.addLayout(toolbar)
        self._build_project_filters(layout)

        content = QSplitter(Qt.Horizontal)
        content.setChildrenCollapsible(False)
        content.setHandleWidth(8)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self.table = QTableView()
        self.model = ProjectTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        style_table(self.table)
        left_layout.addWidget(self.table)

        right_panel = self._build_project_resource_panel()
        right_panel.setMinimumWidth(360)

        content.addWidget(left_panel)
        content.addWidget(right_panel)
        content.setStretchFactor(0, 5)
        content.setStretchFactor(1, 3)
        content.setSizes([900, 520])
        layout.addWidget(content, 1)

        # signal connections
        self.btn_new.clicked.connect(
            make_guarded_slot(self, title="Projects", callback=self.create_project)
        )
        self.btn_edit.clicked.connect(
            make_guarded_slot(self, title="Projects", callback=self.edit_project)
        )
        self.btn_delete.clicked.connect(
            make_guarded_slot(self, title="Projects", callback=self.delete_project)
        )
        self.btn_refresh.clicked.connect(self.reload_projects)
        self.table.selectionModel().selectionChanged.connect(self._on_project_selection_changed)

        apply_permission_hint(
            self.btn_new,
            allowed=self._can_manage_projects,
            missing_permission="project.manage",
        )
        apply_permission_hint(
            self.btn_edit,
            allowed=self._can_manage_projects,
            missing_permission="project.manage",
        )
        apply_permission_hint(
            self.btn_delete,
            allowed=self._can_manage_projects,
            missing_permission="project.manage",
        )
        self._sync_actions()

    def reload_projects(self):
        selected = self._get_selected_project()
        selected_id = selected.id if selected else None
        self._all_projects = self._project_service.list_projects()
        self._render_project_rows(preferred_project_id=selected_id)

    def _on_project_changed_event(self, _project_id: str) -> None:
        self.reload_projects()

    def _on_resources_changed_event(self, _resource_id: str) -> None:
        self._reload_project_resource_panel_for_selected_project()

    def _on_project_selection_changed(self, *_args) -> None:
        ProjectResourcePanelMixin._on_project_selection_changed(self, *_args)
        self._sync_actions()

    def _get_selected_project(self) -> Optional[Project]:
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return None
        row = indexes[0].row()
        return self.model.get_project(row)

    def _sync_actions(self) -> None:
        has_project = self._get_selected_project() is not None
        self.btn_new.setEnabled(self._can_manage_projects)
        self.btn_edit.setEnabled(self._can_manage_projects and has_project)
        self.btn_delete.setEnabled(self._can_manage_projects and has_project)

