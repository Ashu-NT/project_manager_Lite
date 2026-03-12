from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.domain.enums import TaskStatus
from ui.dashboard.styles import dashboard_action_button_style, dashboard_meta_chip_style
from ui.shared.guards import apply_permission_hint, make_guarded_slot
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG
from ui.task.models import TaskTableModel


class TaskLayoutMixin:
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(
            CFG.MARGIN_MD,
            CFG.MARGIN_MD,
            CFG.MARGIN_MD,
            CFG.MARGIN_MD,
        )

        top = QHBoxLayout()
        scope_badge = QLabel("TASK SCOPE")
        scope_badge.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        top.addWidget(scope_badge)
        self.project_combo = QComboBox()
        self.project_combo.setSizePolicy(CFG.INPUT_POLICY)
        self.project_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_reload_projects = QPushButton(CFG.RELOAD_PROJECTS_LABEL)
        top.addWidget(QLabel("Project"))
        top.addWidget(self.project_combo)
        top.addWidget(self.btn_reload_projects)
        top.addStretch()
        self.btn_refresh_tasks = QPushButton(CFG.REFRESH_TASKS_LABEL)
        self.lbl_mentions = QLabel("Mentions: 0")
        self.lbl_mentions.setStyleSheet(dashboard_meta_chip_style())
        top.addWidget(self.lbl_mentions)
        top.addWidget(self.btn_refresh_tasks)

        toolbar = QHBoxLayout()
        actions_badge = QLabel("EXECUTION")
        actions_badge.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        toolbar.addWidget(actions_badge)
        self.btn_new = QPushButton(CFG.NEW_TASK_LABEL)
        self.btn_edit = QPushButton(CFG.EDIT_LABEL)
        self.btn_delete = QPushButton(CFG.DELETE_LABEL)
        self.btn_progress = QPushButton(CFG.UPDATE_PROGRESS_LABEL)
        self.btn_comments = QPushButton("Comments")
        self.bulk_status_combo = QComboBox()
        self.bulk_status_combo.setMinimumWidth(140)
        self.bulk_status_combo.addItem("Bulk: To Do", userData=TaskStatus.TODO.value)
        self.bulk_status_combo.addItem("Bulk: In Progress", userData=TaskStatus.IN_PROGRESS.value)
        self.bulk_status_combo.addItem("Bulk: Done", userData=TaskStatus.DONE.value)
        self.btn_bulk_status = QPushButton("Apply Status")
        self.btn_bulk_delete = QPushButton("Bulk Delete")
        self.btn_undo = QPushButton("Undo")
        self.btn_redo = QPushButton("Redo")

        for btn in [
            self.btn_reload_projects,
            self.btn_refresh_tasks,
            self.btn_new,
            self.btn_edit,
            self.btn_delete,
            self.btn_progress,
            self.btn_comments,
            self.btn_bulk_status,
            self.btn_bulk_delete,
            self.btn_undo,
            self.btn_redo,
        ]:
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.bulk_status_combo.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.bulk_status_combo.setFixedHeight(CFG.INPUT_HEIGHT)
        self.btn_new.setStyleSheet(dashboard_action_button_style("primary"))
        for btn in (
            self.btn_reload_projects,
            self.btn_refresh_tasks,
            self.btn_edit,
            self.btn_progress,
            self.btn_comments,
            self.btn_bulk_status,
            self.btn_undo,
            self.btn_redo,
        ):
            btn.setStyleSheet(dashboard_action_button_style("secondary"))
        for btn in (self.btn_delete, self.btn_bulk_delete):
            btn.setStyleSheet(dashboard_action_button_style("danger"))

        toolbar.addWidget(self.btn_new)
        toolbar.addWidget(self.btn_edit)
        toolbar.addWidget(self.btn_progress)
        toolbar.addWidget(self.btn_delete)
        toolbar.addWidget(self.btn_comments)
        toolbar.addStretch()
        history_badge = QLabel("HISTORY")
        history_badge.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        toolbar.addWidget(history_badge)
        toolbar.addWidget(self.btn_undo)
        toolbar.addWidget(self.btn_redo)

        bulk_row = QHBoxLayout()
        bulk_badge = QLabel("BULK")
        bulk_badge.setStyleSheet(CFG.DASHBOARD_KPI_TITLE_STYLE)
        bulk_row.addWidget(bulk_badge)
        bulk_row.addWidget(self.bulk_status_combo)
        bulk_row.addWidget(self.btn_bulk_status)
        bulk_row.addWidget(self.btn_bulk_delete)
        bulk_row.addStretch()

        controls = QWidget()
        self.task_controls_card = controls
        controls.setObjectName("taskControlSurface")
        controls.setSizePolicy(CFG.H_EXPAND_V_FIXED)
        controls.setStyleSheet(
            f"""
            QWidget#taskControlSurface {{
                background-color: {CFG.COLOR_BG_SURFACE};
                border: 1px solid {CFG.COLOR_BORDER};
                border-radius: 12px;
            }}
            """
        )
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM, CFG.MARGIN_SM)
        controls_layout.setSpacing(CFG.SPACING_SM)
        controls_layout.addLayout(top)
        controls_layout.addLayout(toolbar)
        controls_layout.addLayout(bulk_row)
        root.addWidget(controls)
        self._build_task_filters(root)

        self.table = QTableView()
        self.model = TaskTableModel()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        style_table(self.table)

        self._assignment_panel = self._build_assignment_panel()
        self._assignment_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._assignment_panel.setMinimumWidth(320)

        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.setHandleWidth(8)
        self.main_splitter.addWidget(self.table)
        self.main_splitter.addWidget(self._assignment_panel)
        self.main_splitter.setStretchFactor(0, 5)
        self.main_splitter.setStretchFactor(1, 3)
        self.main_splitter.setSizes([980, 520])
        root.addWidget(self.main_splitter, 1)

        self.btn_reload_projects.clicked.connect(self._load_projects)
        self.project_combo.currentIndexChanged.connect(self._on_project_changed)
        self.btn_refresh_tasks.clicked.connect(self.reload_tasks)
        self.btn_new.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.create_task)
        )
        self.btn_edit.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.edit_task)
        )
        self.btn_delete.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.delete_task)
        )
        self.btn_progress.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.update_progress)
        )
        self.btn_bulk_status.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.apply_bulk_status)
        )
        self.btn_bulk_delete.clicked.connect(
            make_guarded_slot(self, title="Tasks", callback=self.bulk_delete_tasks)
        )
        self.btn_undo.clicked.connect(self.undo_last_task_action)
        self.btn_redo.clicked.connect(self.redo_last_task_action)
        self.btn_comments.clicked.connect(self._open_task_collaboration)
        self.table.selectionModel().selectionChanged.connect(self._on_task_selection_changed)

        apply_permission_hint(
            self.btn_new,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_edit,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_delete,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_progress,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_bulk_status,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        apply_permission_hint(
            self.btn_bulk_delete,
            allowed=self._can_manage_tasks,
            missing_permission="task.manage",
        )
        self._apply_accessibility_labels()
        self._setup_shortcuts()
        self._sync_toolbar_actions()


__all__ = ["TaskLayoutMixin"]
