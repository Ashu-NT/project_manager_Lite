from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QTabWidget,
)

from core.platform.notifications.domain_events import domain_events
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.access.policy import PROJECT_SCOPE_ROLE_CHOICES
from core.platform.access import AccessControlService
from core.platform.auth import AuthService
from core.platform.auth import UserSessionContext
from core.modules.project_management.services.project import ProjectService
from ui.platform.shared.guards import apply_permission_hint, has_permission
from ui.platform.shared.styles.style_utils import style_table
from ui.platform.shared.styles.ui_config import UIConfig as CFG


class AccessTab(QWidget):
    def __init__(
        self,
        *,
        access_service: AccessControlService,
        auth_service: AuthService,
        project_service: ProjectService,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._access_service = access_service
        self._auth_service = auth_service
        self._project_service = project_service
        self._user_session = user_session
        self._project_management_available = True
        self._can_manage_memberships = has_permission(self._user_session, "access.manage")
        self._can_unlock_users = has_permission(self._user_session, "auth.manage") or has_permission(
            self._user_session,
            "security.manage",
        )
        self._can_view_user_security = any(
            has_permission(self._user_session, permission_code)
            for permission_code in ("auth.read", "auth.manage", "access.manage", "security.manage")
        )
        self._user_by_id: dict[str, object] = {}
        self._setup_ui()
        self.reload_data()
        domain_events.project_changed.connect(self._on_domain_change)
        domain_events.auth_changed.connect(self._on_domain_change)
        domain_events.access_changed.connect(self._on_domain_change)
        domain_events.modules_changed.connect(self._on_domain_change)

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(CFG.SPACING_MD)
        root.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("Access Control")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel(
            "Manage project-scoped memberships and inspect login security state for user accounts."
        )
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)
        
        self.access_tabs = QTabWidget()
        self.access_tabs.setObjectName("AccessControlTabs")

        controls_box = QWidget()
        controls_layout = QVBoxLayout(controls_box)
        controls_layout.setSpacing(CFG.SPACING_SM)

        row = QGridLayout()
        row.setHorizontalSpacing(CFG.SPACING_MD)
        row.setVerticalSpacing(CFG.SPACING_SM)
        self.project_combo = QComboBox()
        self.user_combo = QComboBox()
        self.role_combo = QComboBox()
        for role_name in PROJECT_SCOPE_ROLE_CHOICES:
            self.role_combo.addItem(role_name.replace("_", " ").title(), userData=role_name)
        row.addWidget(QLabel("Project"), 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.project_combo, 0, 1)
        row.addWidget(QLabel("User"), 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.user_combo, 0, 3)
        row.addWidget(QLabel("Scope Role"), 0, 4, alignment=Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.role_combo, 0, 5)
        controls_layout.addLayout(row)

        button_row = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_assign = QPushButton("Assign Membership")
        self.btn_remove = QPushButton("Remove Membership")
        for button in (self.btn_refresh, self.btn_assign, self.btn_remove):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            button_row.addWidget(button)
        button_row.addStretch()
        controls_layout.addLayout(button_row)

        self.membership_hint = QLabel("")
        self.membership_hint.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.membership_hint.setWordWrap(True)
        controls_layout.addWidget(self.membership_hint)

        self.membership_table = QTableWidget(0, 3)
        self.membership_table.setHorizontalHeaderLabels(["User", "Scope Role", "Permissions"])
        self.membership_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.membership_table.setSelectionMode(QTableWidget.SingleSelection)
        self.membership_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.membership_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.membership_table)
        self.membership_table.setEnabled(self._can_manage_memberships)
        controls_layout.addWidget(self.membership_table)
        
        security_box = QWidget()
        security_layout = QVBoxLayout(security_box)
        security_layout.setSpacing(CFG.SPACING_SM)
        security_header = QHBoxLayout()
        self.security_hint = QLabel("Unlock accounts after lockout or inspect active session expiry state.")
        self.security_hint.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.btn_unlock = QPushButton("Unlock Selected User")
        self.btn_unlock.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_unlock.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        security_header.addWidget(self.security_hint, 1)
        security_header.addWidget(self.btn_unlock)
        security_layout.addLayout(security_header)

        self.security_table = QTableWidget(0, 5)
        self.security_table.setHorizontalHeaderLabels(
            ["User", "Active", "Failed Attempts", "Locked Until", "Session Expires"]
        )
        self.security_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.security_table.setSelectionMode(QTableWidget.SingleSelection)
        self.security_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.security_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.security_table)
        self.security_table.setEnabled(self._can_view_user_security)
        security_layout.addWidget(self.security_table)
        
        self.access_tabs.addTab(controls_box,"Project Memberships")
        self.access_tabs.addTab(security_box,"Account Security")
        
        root.addWidget(self.access_tabs, 1)

        self.project_combo.currentIndexChanged.connect(self._reload_memberships)
        self.btn_refresh.clicked.connect(self.reload_data)
        self.btn_assign.clicked.connect(self._assign_membership)
        self.btn_remove.clicked.connect(self._remove_membership)
        self.btn_unlock.clicked.connect(self._unlock_selected_user)
        for widget in (self.project_combo, self.user_combo, self.role_combo):
            widget.setEnabled(self._can_manage_memberships)
        self.membership_table.itemSelectionChanged.connect(self._sync_membership_controls)
        apply_permission_hint(
            self.btn_assign,
            allowed=self._can_manage_memberships,
            missing_permission="access.manage",
        )
        apply_permission_hint(
            self.btn_remove,
            allowed=self._can_manage_memberships,
            missing_permission="access.manage",
        )
        apply_permission_hint(
            self.btn_unlock,
            allowed=self._can_unlock_users,
            missing_permission="auth.manage or security.manage",
        )
        self._sync_membership_controls()

    def reload_data(self) -> None:
        projects = []
        users = []
        project_management_available = True
        try:
            if self._can_manage_memberships:
                try:
                    projects = self._project_service.list_projects()
                except BusinessRuleError as exc:
                    if exc.code != "MODULE_DISABLED":
                        raise
                    project_management_available = False
            if self._can_view_user_security:
                users = self._auth_service.list_users()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Access Control", f"Failed to load access data:\n{exc}")
            return

        self._project_management_available = project_management_available
        self._user_by_id = {user.id: user for user in users}
        selected_project = self.project_combo.currentData()
        selected_user = self.user_combo.currentData()

        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for project in projects:
            self.project_combo.addItem(project.name, userData=project.id)
        self.project_combo.blockSignals(False)

        self.user_combo.clear()
        for user in users:
            self.user_combo.addItem(user.username, userData=user.id)

        if selected_project:
            idx = self.project_combo.findData(selected_project)
            if idx >= 0:
                self.project_combo.setCurrentIndex(idx)
        if selected_user:
            idx = self.user_combo.findData(selected_user)
            if idx >= 0:
                self.user_combo.setCurrentIndex(idx)

        self._reload_memberships()
        self._reload_security_table()
        self._sync_membership_controls()

    def _reload_memberships(self) -> None:
        if not self._can_manage_memberships or not self._project_management_available:
            self.membership_table.setRowCount(0)
            self._sync_membership_controls()
            return
        project_id = str(self.project_combo.currentData() or "").strip()
        if not project_id:
            self.membership_table.setRowCount(0)
            self._sync_membership_controls()
            return
        try:
            rows = self._access_service.list_project_memberships(project_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        self.membership_table.setRowCount(len(rows))
        for row_idx, membership in enumerate(rows):
            user = self._user_by_id.get(membership.user_id)
            values = [
                getattr(user, "username", membership.user_id),
                membership.scope_role.title(),
                ", ".join(membership.permission_codes),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, membership.user_id)
                self.membership_table.setItem(row_idx, col, item)
        self._sync_membership_controls()

    def _reload_security_table(self) -> None:
        if not self._can_view_user_security:
            self.security_table.setRowCount(0)
            return
        users = list(self._user_by_id.values())
        self.security_table.setRowCount(len(users))
        for row_idx, user in enumerate(users):
            values = [
                getattr(user, "username", ""),
                "Yes" if bool(getattr(user, "is_active", False)) else "No",
                str(int(getattr(user, "failed_login_attempts", 0) or 0)),
                getattr(getattr(user, "locked_until", None), "isoformat", lambda: "-")(),
                getattr(getattr(user, "session_expires_at", None), "isoformat", lambda: "-")(),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value if value else "-")
                if col == 0:
                    item.setData(Qt.UserRole, getattr(user, "id", ""))
                self.security_table.setItem(row_idx, col, item)

    def _assign_membership(self) -> None:
        project_id = str(self.project_combo.currentData() or "").strip()
        user_id = str(self.user_combo.currentData() or "").strip()
        scope_role = str(self.role_combo.currentData() or "viewer").strip()
        if not project_id or not user_id:
            QMessageBox.information(self, "Access Control", "Select a project and user first.")
            return
        try:
            self._access_service.assign_project_membership(
                project_id=project_id,
                user_id=user_id,
                scope_role=scope_role,
            )
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        self._reload_memberships()

    def _remove_membership(self) -> None:
        row = self.membership_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Access Control", "Select a membership to remove.")
            return
        project_id = str(self.project_combo.currentData() or "").strip()
        item = self.membership_table.item(row, 0)
        user_id = str(item.data(Qt.UserRole) or "") if item is not None else ""
        if not project_id or not user_id:
            return
        try:
            self._access_service.remove_project_membership(project_id=project_id, user_id=user_id)
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        self._reload_memberships()

    def _unlock_selected_user(self) -> None:
        if not self._can_unlock_users:
            QMessageBox.information(
                self,
                "Access Control",
                "Unlocking accounts requires auth.manage or security.manage.",
            )
            return
        row = self.security_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Access Control", "Select a user to unlock.")
            return
        item = self.security_table.item(row, 0)
        user_id = str(item.data(Qt.UserRole) or "") if item is not None else ""
        if not user_id:
            return
        try:
            self._auth_service.unlock_user_account(user_id)
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        self.reload_data()

    def _on_domain_change(self, _payload: str) -> None:
        self.reload_data()

    def _sync_membership_controls(self) -> None:
        has_projects = self.project_combo.count() > 0
        has_selection = self.membership_table.currentRow() >= 0
        can_edit_memberships = (
            self._can_manage_memberships
            and self._project_management_available
            and has_projects
        )
        self.project_combo.setEnabled(can_edit_memberships)
        self.user_combo.setEnabled(can_edit_memberships)
        self.role_combo.setEnabled(can_edit_memberships)
        self.membership_table.setEnabled(self._can_manage_memberships and self._project_management_available)
        self.btn_assign.setEnabled(can_edit_memberships)
        self.btn_remove.setEnabled(can_edit_memberships and has_selection)
        if not self._can_manage_memberships:
            self.membership_hint.setText("Managing project memberships requires access.manage.")
        elif not self._project_management_available:
            self.membership_hint.setText(
                "Project Management is disabled. Enable it in Modules before managing project memberships."
            )
        elif not has_projects:
            self.membership_hint.setText("No projects are available yet. Create a project to assign memberships.")
        else:
            self.membership_hint.setText(
                "Assign project-scoped access and remove memberships from the selected project."
            )


__all__ = ["AccessTab"]
