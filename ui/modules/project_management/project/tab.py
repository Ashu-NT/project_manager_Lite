from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.core.platform.notifications.domain_events import domain_events
from src.core.modules.project_management.domain.projects.project import Project
from src.core.platform.auth import UserSessionContext
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import ProjectResourceService
from src.core.modules.project_management.infrastructure.importers import DataImportService
from src.core.modules.project_management.infrastructure.reporting import ReportingService
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.application.tasks import TaskService
from ui.modules.project_management.dashboard.styles import dashboard_action_button_style, dashboard_badge_style, dashboard_meta_chip_style
from ui.modules.project_management.project.actions import ProjectActionsMixin
from ui.modules.project_management.project.dialogs import ProjectEditDialog  # noqa: F401
from ui.modules.project_management.project.filtering import ProjectFiltersMixin
from ui.modules.project_management.project.import_actions import ProjectImportActionsMixin
from ui.modules.project_management.project.models import ProjectTableModel
from ui.modules.project_management.project.resource_panel import ProjectResourcePanelMixin
from ui.modules.project_management.shared.domain_event_filters import is_project_management_domain_event
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.style_utils import style_table
from src.ui.shared.formatting.ui_config import UIConfig as CFG

class ProjectTab(
    ProjectImportActionsMixin,
    ProjectActionsMixin,
    ProjectFiltersMixin,
    ProjectResourcePanelMixin,
    QWidget,
):
    def __init__(
        self,
        project_service: ProjectService,
        task_service: TaskService,
        reporting_service: ReportingService,
        project_resource_service: ProjectResourceService,
        resource_service: ResourceService,
        data_import_service: DataImportService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._project_service: ProjectService = project_service
        self._task_service: TaskService = task_service
        self._reporting_service: ReportingService = reporting_service
        self._project_resource_service: ProjectResourceService = project_resource_service
        self._resource_service: ResourceService = resource_service
        self._data_import_service: DataImportService = data_import_service
        self._user_session = user_session
        self._can_manage_projects = has_permission(self._user_session, "project.manage")
        self._can_manage_project_resources = self._can_manage_projects
        self._all_projects: list[Project] = []

        self._setup_ui()
        self.reload_projects()
        self._sync_actions()
        domain_events.domain_changed.connect(self._on_domain_change)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(
            CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD
        )

        header = QWidget()
        header.setObjectName("projectHeaderCard")
        header.setStyleSheet(
            f"""
            QWidget#projectHeaderCard {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_SM, CFG.MARGIN_MD, CFG.MARGIN_SM)
        header_layout.setSpacing(CFG.SPACING_MD)
        intro = QVBoxLayout()
        intro.setSpacing(CFG.SPACING_XS)
        eyebrow = QLabel("PROJECTS")
        eyebrow.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        intro.addWidget(eyebrow)
        title = QLabel("Project Workspace")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        intro.addWidget(title)
        subtitle = QLabel("Manage project delivery, imports, status updates, and staffing from one workspace.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        intro.addWidget(subtitle)
        header_layout.addLayout(intro, 1)
        status_layout = QVBoxLayout()
        status_layout.setSpacing(CFG.SPACING_SM)
        self.project_scope_badge = QLabel("All Statuses")
        self.project_scope_badge.setStyleSheet(dashboard_badge_style(CFG.COLOR_ACCENT))
        self.project_count_badge = QLabel("0 visible")
        self.project_count_badge.setStyleSheet(dashboard_meta_chip_style())
        access_label = "Manage Enabled" if self._can_manage_projects else "Read Only"
        self.project_access_badge = QLabel(access_label)
        self.project_access_badge.setStyleSheet(dashboard_meta_chip_style())
        status_layout.addWidget(self.project_scope_badge, 0)
        status_layout.addWidget(self.project_count_badge, 0)
        status_layout.addWidget(self.project_access_badge, 0)
        status_layout.addStretch(1)
        header_layout.addLayout(status_layout)
        layout.addWidget(header)

        controls = QWidget()
        controls.setObjectName("projectControlSurface")
        controls.setStyleSheet(
            f"""
            QWidget#projectControlSurface {{
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
        self.btn_new = QPushButton(CFG.NEW_PROJECT_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_update_status = QPushButton(CFG.UPDATE_PROJECT_STATUS_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_import_csv = QPushButton("Import CSV")
        self.btn_refresh = QPushButton(CFG.REFRESH_PROJECTS_LABEL)

        for btn in (
            self.btn_new,
            self.btn_edit,
            self.btn_update_status,
            self.btn_delete,
            self.btn_import_csv,
            self.btn_refresh,
        ):
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_edit.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_update_status.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_delete.setStyleSheet(dashboard_action_button_style("danger"))
        self.btn_import_csv.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_update_status)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_import_csv)
        toolbar.addStretch()
        toolbar.addWidget(self.btn_refresh)

        controls_layout.addLayout(toolbar)
        self._build_project_filters(controls_layout)
        self.btn_clear_project_filters.setStyleSheet(dashboard_action_button_style("secondary"))
        layout.addWidget(controls)

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
        self.btn_update_status.clicked.connect(
            make_guarded_slot(self, title="Projects", callback=self.update_project_status)
        )
        self.btn_delete.clicked.connect(
            make_guarded_slot(self, title="Projects", callback=self.delete_project)
        )
        self.btn_import_csv.clicked.connect(
            make_guarded_slot(self, title="Projects", callback=self.import_csv_data)
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
            self.btn_update_status,
            allowed=self._can_manage_projects,
            missing_permission="project.manage",
        )
        apply_permission_hint(
            self.btn_delete,
            allowed=self._can_manage_projects,
            missing_permission="project.manage",
        )
        apply_permission_hint(
            self.btn_import_csv,
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

    def _on_domain_change(self, event) -> None:
        if is_project_management_domain_event(event, "project"):
            self._on_project_changed_event(event.entity_id)
        elif is_project_management_domain_event(event, "resource"):
            self._on_resources_changed_event(event.entity_id)

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
        self.btn_update_status.setEnabled(self._can_manage_projects and has_project)
        self.btn_delete.setEnabled(self._can_manage_projects and has_project)
        self.btn_import_csv.setEnabled(self._can_manage_projects)

    def _update_project_header_badges(self, visible_projects: list[Project]) -> None:
        status_label = self.project_status_filter.currentText() if self.project_status_filter.currentIndex() > 0 else "All Statuses"
        self.project_scope_badge.setText(status_label)
        self.project_count_badge.setText(f"{len(visible_projects)} visible")
