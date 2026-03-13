from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.events.domain_events import domain_events
from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.services.access import AccessControlService
from core.services.auth import AuthService
from core.services.auth import UserSessionContext
from core.services.project import ProjectService
from ui.shared.guards import apply_permission_hint, has_permission
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


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
        self._can_unlock_users = has_permission(self._user_session, "auth.manage")
        self._user_by_id: dict[str, object] = {}
        self._setup_ui()
        self.reload_data()
        domain_events.project_changed.connect(self._on_domain_change)
        domain_events.auth_changed.connect(self._on_domain_change)
        domain_events.access_changed.connect(self._on_domain_change)

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

        controls_box = QGroupBox("Project Memberships")
        controls_layout = QVBoxLayout(controls_box)
        controls_layout.setSpacing(CFG.SPACING_SM)

        row = QGridLayout()
        row.setHorizontalSpacing(CFG.SPACING_MD)
        row.setVerticalSpacing(CFG.SPACING_SM)
        self.project_combo = QComboBox()
        self.user_combo = QComboBox()
        self.role_combo = QComboBox()
        for role_name in ("viewer", "editor", "owner"):
            self.role_combo.addItem(role_name.title(), userData=role_name)
        row.addWidget(QLabel("Project"), 0, 0)
        row.addWidget(self.project_combo, 0, 1)
        row.addWidget(QLabel("User"), 0, 2)
        row.addWidget(self.user_combo, 0, 3)
        row.addWidget(QLabel("Scope Role"), 1, 0)
        row.addWidget(self.role_combo, 1, 1)
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

        self.membership_table = QTableWidget(0, 3)
        self.membership_table.setHorizontalHeaderLabels(["User", "Scope Role", "Permissions"])
        self.membership_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.membership_table.setSelectionMode(QTableWidget.SingleSelection)
        self.membership_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.membership_table.horizontalHeader().setStretchLastSection(True)
        style_table(self.membership_table)
        controls_layout.addWidget(self.membership_table)
        root.addWidget(controls_box)

        security_box = QGroupBox("Account Security")
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
        security_layout.addWidget(self.security_table)
        root.addWidget(security_box, 1)

        self.project_combo.currentIndexChanged.connect(self._reload_memberships)
        self.btn_refresh.clicked.connect(self.reload_data)
        self.btn_assign.clicked.connect(self._assign_membership)
        self.btn_remove.clicked.connect(self._remove_membership)
        self.btn_unlock.clicked.connect(self._unlock_selected_user)
        apply_permission_hint(
            self.btn_unlock,
            allowed=self._can_unlock_users,
            missing_permission="auth.manage",
        )

    def reload_data(self) -> None:
        try:
            projects = self._project_service.list_projects()
            users = self._auth_service.list_users()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Access Control", f"Failed to load access data:\n{exc}")
            return

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

    def _reload_memberships(self) -> None:
        project_id = str(self.project_combo.currentData() or "").strip()
        if not project_id:
            self.membership_table.setRowCount(0)
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

    def _reload_security_table(self) -> None:
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
            QMessageBox.information(self, "Access Control", "Unlocking accounts requires auth.manage.")
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


__all__ = ["AccessTab"]
