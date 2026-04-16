from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.platform.access import AccessControlService
from src.core.platform.auth import AuthService
from src.core.platform.auth import UserSessionContext
from core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.platform.notifications.domain_events import domain_events
from ui.modules.project_management.dashboard.styles import (
    dashboard_action_button_style,
    dashboard_meta_chip_style,
)
from ui.platform.admin.shared_header import build_admin_header
from ui.platform.admin.shared_surface import build_admin_surface_card, build_admin_table
from ui.platform.shared.guards import apply_permission_hint, has_permission
from ui.platform.shared.styles.ui_config import UIConfig as CFG


ScopeOptionLoader = Callable[[], list[tuple[str, str]]]


class AccessTab(QWidget):
    def __init__(
        self,
        *,
        access_service: AccessControlService,
        auth_service: AuthService,
        project_service: object | None = None,
        scope_type_choices: tuple[tuple[str, str], ...] | None = None,
        scope_option_loaders: dict[str, ScopeOptionLoader] | None = None,
        scope_disabled_hints: dict[str, str] | None = None,
        show_access_tab: bool = True,
        show_security_tab: bool = True,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if not show_access_tab and not show_security_tab:
            raise ValueError("AccessTab requires at least one visible section.")
        self._access_service = access_service
        self._auth_service = auth_service
        self._project_service = project_service
        self._user_session = user_session
        self._show_access_tab = bool(show_access_tab)
        self._show_security_tab = bool(show_security_tab)
        self._scope_type_choices = scope_type_choices or (("Project", "project"),)
        self._scope_option_loaders = dict(scope_option_loaders or {})
        if "project" not in self._scope_option_loaders and self._project_service is not None:
            self._scope_option_loaders["project"] = self._load_project_scope_options
        self._scope_disabled_hints = dict(scope_disabled_hints or {})
        self._scope_disabled_hints.setdefault(
            "project",
            "Project Management is disabled. Enable it in Modules before managing project-scoped access.",
        )
        self._scope_availability: dict[str, bool] = {
            scope_type: True
            for _label, scope_type in self._scope_type_choices
        }
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

        if self._show_access_tab and self._show_security_tab:
            eyebrow_text = "IDENTITY & ACCESS"
            title_text = "Access Control"
            subtitle_text = "Manage scoped access grants and inspect login security state for user accounts."
            scope_badge_text = "Combined Surface"
        elif self._show_access_tab:
            eyebrow_text = "PLATFORM ACCESS"
            title_text = "Scoped Access"
            subtitle_text = "Manage scope-specific access grants across enabled platform and module scopes."
            scope_badge_text = "Multi-Scope Grants"
        else:
            eyebrow_text = "PLATFORM SECURITY"
            title_text = "Account Security"
            subtitle_text = "Inspect lockout, session, and account-security state for user accounts."
            scope_badge_text = "Session Governance"

        access_label = "Manage Enabled" if (self._can_manage_memberships or self._can_unlock_users) else "Read Only"
        build_admin_header(
            self,
            root,
            object_name="accessAdminHeaderCard",
            eyebrow_text=eyebrow_text,
            title_text=title_text,
            subtitle_text=subtitle_text,
            badge_specs=(
                ("header_scope_badge", scope_badge_text, "accent"),
                ("header_access_badge", access_label, "meta"),
                ("header_mode_badge", "Live Session View" if self._show_security_tab else "Grant Directory", "meta"),
            ),
        )

        controls_box, controls_layout = build_admin_surface_card(object_name="accessAdminControlSurface", alt=True)

        controls_title = QLabel("Grant Scoped Access")
        controls_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        controls_description = QLabel(
            "Select a scope, user, and scope role to manage membership and effective permissions."
        )
        controls_description.setStyleSheet(CFG.INFO_TEXT_STYLE)
        controls_description.setWordWrap(True)
        controls_layout.addWidget(controls_title)
        controls_layout.addWidget(controls_description)

        row = QGridLayout()
        row.setHorizontalSpacing(CFG.SPACING_MD)
        row.setVerticalSpacing(CFG.SPACING_SM)
        self.scope_type_combo = QComboBox()
        for label, scope_type in self._scope_type_choices:
            self.scope_type_combo.addItem(label, userData=scope_type)
        self.scope_combo = QComboBox()
        self.project_combo = self.scope_combo
        self.user_combo = QComboBox()
        self.role_combo = QComboBox()
        row.setColumnStretch(1, 1)
        row.setColumnStretch(3, 1)
        row.addWidget(QLabel("Scope Type"), 0, 0, alignment=Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.scope_type_combo, 0, 1)
        row.addWidget(QLabel("Scope"), 0, 2, alignment=Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.scope_combo, 0, 3)
        row.addWidget(QLabel("User"), 1, 0, alignment=Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.user_combo, 1, 1)
        row.addWidget(QLabel("Scope Role"), 1, 2, alignment=Qt.AlignmentFlag.AlignRight)
        row.addWidget(self.role_combo, 1, 3)
        controls_layout.addLayout(row)

        button_row = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_assign = QPushButton("Assign Membership")
        self.btn_remove = QPushButton("Remove Membership")
        for button in (self.btn_refresh, self.btn_assign, self.btn_remove):
            button.setFixedHeight(CFG.BUTTON_HEIGHT)
            button.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
            button.setMinimumWidth(CFG.BUTTON_MIN_WIDTH_SM)
            button_row.addWidget(button)
        self.btn_assign.setStyleSheet(dashboard_action_button_style("primary"))
        self.btn_remove.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_refresh.setStyleSheet(dashboard_action_button_style("secondary"))
        button_row.addStretch()
        controls_layout.addLayout(button_row)

        self.membership_hint = QLabel("")
        self.membership_hint.setStyleSheet(CFG.NOTE_STYLE_SHEET)
        self.membership_hint.setWordWrap(True)
        controls_layout.addWidget(self.membership_hint)

        self.membership_table = build_admin_table(
            headers=("User", "Scope Role", "Permissions"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
            ),
        )
        self.membership_table.setEnabled(self._can_manage_memberships)
        controls_layout.addWidget(self.membership_table)

        security_box, security_layout = build_admin_surface_card(object_name="accessAdminSecuritySurface", alt=True)

        security_title = QLabel("Session And Lockout Controls")
        security_title.setStyleSheet(CFG.SECTION_BOLD_MARGIN_STYLE)
        self.security_hint = QLabel(
            "Inspect account state, unlock locked users, and revoke live sessions when access needs to be cut immediately."
        )
        self.security_hint.setStyleSheet(CFG.INFO_TEXT_STYLE)
        self.security_hint.setWordWrap(True)
        self.btn_unlock = QPushButton("Unlock Selected User")
        self.btn_revoke_sessions = QPushButton("Revoke Sessions")
        self.btn_unlock.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_unlock.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_revoke_sessions.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_revoke_sessions.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.btn_unlock.setMinimumWidth(CFG.BUTTON_MIN_WIDTH_SM)
        self.btn_revoke_sessions.setMinimumWidth(CFG.BUTTON_MIN_WIDTH_SM)
        self.btn_unlock.setStyleSheet(dashboard_action_button_style("secondary"))
        self.btn_revoke_sessions.setStyleSheet(dashboard_action_button_style("secondary"))
        security_layout.addWidget(security_title)
        security_layout.addWidget(self.security_hint)

        security_actions = QHBoxLayout()
        security_actions.addStretch()
        security_actions.addWidget(self.btn_revoke_sessions)
        security_actions.addWidget(self.btn_unlock)
        security_layout.addLayout(security_actions)

        self.security_table = build_admin_table(
            headers=("User", "Active", "Failed Attempts", "Locked Until", "Session Expires"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
            ),
        )
        self.security_table.setEnabled(self._can_view_user_security)
        security_layout.addWidget(self.security_table)

        controls_box.setVisible(self._show_access_tab)
        security_box.setVisible(self._show_security_tab)
        root.addWidget(controls_box, 3)
        root.addWidget(security_box, 2)

        self.scope_type_combo.currentIndexChanged.connect(self._on_scope_type_changed)
        self.scope_combo.currentIndexChanged.connect(self._reload_memberships)
        self.btn_refresh.clicked.connect(self.reload_data)
        self.btn_assign.clicked.connect(self._assign_membership)
        self.btn_remove.clicked.connect(self._remove_membership)
        self.btn_revoke_sessions.clicked.connect(self._revoke_sessions_for_selected_user)
        self.btn_unlock.clicked.connect(self._unlock_selected_user)
        for widget in (self.scope_type_combo, self.scope_combo, self.user_combo, self.role_combo):
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
        apply_permission_hint(
            self.btn_revoke_sessions,
            allowed=self._can_unlock_users,
            missing_permission="auth.manage or security.manage",
        )
        self._sync_membership_controls()

    def reload_data(self) -> None:
        users = []
        try:
            if self._can_view_user_security:
                users = self._auth_service.list_users()
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Access Control", f"Failed to load access data:\n{exc}")
            return

        self._user_by_id = {user.id: user for user in users}
        selected_scope_id = self.scope_combo.currentData()
        selected_user = self.user_combo.currentData()

        self.user_combo.clear()
        for user in users:
            self.user_combo.addItem(user.username, userData=user.id)
        if selected_user:
            idx = self.user_combo.findData(selected_user)
            if idx >= 0:
                self.user_combo.setCurrentIndex(idx)

        self._reload_role_choices()
        self._reload_scope_options(selected_scope_id=selected_scope_id)
        self._reload_security_table()
        self._sync_membership_controls()

    def _reload_memberships(self) -> None:
        scope_type = self._current_scope_type()
        if not self._can_manage_memberships or not self._scope_availability.get(scope_type, True):
            self.membership_table.setRowCount(0)
            self._sync_membership_controls()
            return
        scope_id = str(self.scope_combo.currentData() or "").strip()
        if not scope_id:
            self.membership_table.setRowCount(0)
            self._sync_membership_controls()
            return
        try:
            rows = self._access_service.list_scope_grants(scope_type, scope_id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        self.membership_table.setRowCount(len(rows))
        for row_idx, grant in enumerate(rows):
            user = self._user_by_id.get(grant.user_id)
            values = [
                getattr(user, "username", grant.user_id),
                grant.scope_role.title(),
                ", ".join(grant.permission_codes),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, grant.user_id)
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
        scope_type = self._current_scope_type()
        scope_id = str(self.scope_combo.currentData() or "").strip()
        user_id = str(self.user_combo.currentData() or "").strip()
        scope_role = str(self.role_combo.currentData() or "viewer").strip()
        if not scope_id or not user_id:
            QMessageBox.information(self, "Access Control", "Select a scope and user first.")
            return
        try:
            self._access_service.assign_scope_grant(
                scope_type=scope_type,
                scope_id=scope_id,
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
        scope_type = self._current_scope_type()
        scope_id = str(self.scope_combo.currentData() or "").strip()
        item = self.membership_table.item(row, 0)
        user_id = str(item.data(Qt.UserRole) or "") if item is not None else ""
        if not scope_id or not user_id:
            return
        try:
            self._access_service.remove_scope_grant(scope_type=scope_type, scope_id=scope_id, user_id=user_id)
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

    def _revoke_sessions_for_selected_user(self) -> None:
        if not self._can_unlock_users:
            QMessageBox.information(
                self,
                "Access Control",
                "Revoking sessions requires auth.manage or security.manage.",
            )
            return
        row = self.security_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Access Control", "Select a user first.")
            return
        item = self.security_table.item(row, 0)
        user_id = str(item.data(Qt.UserRole) or "") if item is not None else ""
        if not user_id:
            return
        try:
            self._auth_service.revoke_user_sessions(user_id, note="Revoked from Account Security workspace.")
        except (BusinessRuleError, ValidationError, NotFoundError) as exc:
            QMessageBox.warning(self, "Access Control", str(exc))
            return
        self.reload_data()

    def _on_domain_change(self, _payload: str) -> None:
        self.reload_data()

    def _on_scope_type_changed(self) -> None:
        self._reload_role_choices()
        self._reload_scope_options()

    def _reload_role_choices(self) -> None:
        selected_role = self.role_combo.currentData()
        scope_type = self._current_scope_type()
        self.role_combo.clear()
        try:
            role_choices = self._access_service.list_scope_role_choices(scope_type)
        except ValidationError:
            role_choices = ()
        for role_name in role_choices:
            self.role_combo.addItem(role_name.replace("_", " ").title(), userData=role_name)
        if selected_role:
            idx = self.role_combo.findData(selected_role)
            if idx >= 0:
                self.role_combo.setCurrentIndex(idx)
        if self.role_combo.count() == 0:
            self.role_combo.addItem("Viewer", userData="viewer")

    def _reload_scope_options(self, *, selected_scope_id: object | None = None) -> None:
        scope_type = self._current_scope_type()
        options: list[tuple[str, str]] = []
        scope_available = True
        loader = self._scope_option_loaders.get(scope_type)
        if self._can_manage_memberships and loader is not None:
            try:
                options = loader()
            except BusinessRuleError as exc:
                if exc.code == "MODULE_DISABLED":
                    scope_available = False
                else:
                    QMessageBox.warning(self, "Access Control", str(exc))
                    return
            except Exception as exc:
                QMessageBox.critical(self, "Access Control", f"Failed to load scope options:\n{exc}")
                return
        self._scope_availability[scope_type] = scope_available
        self.scope_combo.blockSignals(True)
        self.scope_combo.clear()
        for label, value in options:
            self.scope_combo.addItem(label, userData=value)
        if selected_scope_id:
            idx = self.scope_combo.findData(selected_scope_id)
            if idx >= 0:
                self.scope_combo.setCurrentIndex(idx)
        self.scope_combo.blockSignals(False)
        self._reload_memberships()

    def _sync_membership_controls(self) -> None:
        scope_type = self._current_scope_type()
        has_scopes = self.scope_combo.count() > 0
        has_selection = self.membership_table.currentRow() >= 0
        scope_available = self._scope_availability.get(scope_type, True)
        can_edit_memberships = self._can_manage_memberships and scope_available and has_scopes
        self.scope_type_combo.setEnabled(self._can_manage_memberships and len(self._scope_type_choices) > 1)
        self.scope_combo.setEnabled(can_edit_memberships)
        self.user_combo.setEnabled(can_edit_memberships)
        self.role_combo.setEnabled(can_edit_memberships)
        self.membership_table.setEnabled(self._can_manage_memberships and scope_available)
        self.btn_assign.setEnabled(can_edit_memberships)
        self.btn_remove.setEnabled(can_edit_memberships and has_selection)
        if not self._can_manage_memberships:
            self.membership_hint.setText("Managing scoped access requires access.manage.")
        elif not scope_available:
            self.membership_hint.setText(
                self._scope_disabled_hints.get(
                    scope_type,
                    f"{self.scope_type_combo.currentText()} is unavailable. Enable the owning module first.",
                )
            )
        elif not has_scopes:
            self.membership_hint.setText("No scopes are available yet. Create one before assigning access.")
        else:
            self.membership_hint.setText(
                "Assign scoped access and remove grants from the selected scope."
            )

    def _current_scope_type(self) -> str:
        return str(self.scope_type_combo.currentData() or "project").strip().lower() or "project"

    def _load_project_scope_options(self) -> list[tuple[str, str]]:
        if self._project_service is None or not hasattr(self._project_service, "list_projects"):
            return []
        return [
            (project.name, project.id)
            for project in self._project_service.list_projects()
        ]


__all__ = ["AccessTab"]
