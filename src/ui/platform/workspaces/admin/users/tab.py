from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.api.desktop.platform import (
    DesktopApiError,
    PlatformUserDesktopApi,
    RoleDto,
    UserCreateCommand,
    UserDto,
    UserPasswordResetCommand,
    UserUpdateCommand,
)
from src.core.platform.auth import UserSessionContext
from src.ui.platform.dialogs.admin.users.dialogs import PasswordResetDialog, UserCreateDialog, UserEditDialog
from src.ui.platform.widgets.admin_header import build_admin_header
from src.ui.platform.widgets.admin_surface import ToolbarButtonSpec, build_admin_table, build_admin_toolbar_surface
from src.ui.shared.widgets.guards import apply_permission_hint, has_permission, make_guarded_slot
from src.ui.shared.formatting.ui_config import UIConfig as CFG


class UserAdminTab(QWidget):
    def __init__(
        self,
        *,
        platform_user_api: PlatformUserDesktopApi,
        user_session: UserSessionContext | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._platform_user_api = platform_user_api
        self._user_session = user_session
        self._can_manage_users = has_permission(self._user_session, "auth.manage")
        self._rows: list[UserDto] = []
        self._roles: list[RoleDto] = []
        self._setup_ui()
        self.reload_users()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        access_label = "Manage Enabled" if self._can_manage_users else "Read Only"
        build_admin_header(
            self,
            layout,
            object_name="userAdminHeaderCard",
            eyebrow_text="IDENTITY",
            title_text="User Administration",
            subtitle_text="Manage user accounts, roles, access posture, and active status.",
            badge_specs=(
                ("user_scope_badge", "Account Directory", "accent"),
                ("user_count_badge", "0 users", "meta"),
                ("user_active_badge", "0 active", "meta"),
                ("user_access_badge", access_label, "meta"),
            ),
        )

        build_admin_toolbar_surface(
            self,
            layout,
            object_name="userAdminControlSurface",
            button_specs=(
                ToolbarButtonSpec("btn_new_user", "New User", "primary"),
                ToolbarButtonSpec("btn_edit_user", "Edit User"),
                ToolbarButtonSpec("btn_assign_role", "Assign Role"),
                ToolbarButtonSpec("btn_revoke_role", "Revoke Role"),
                ToolbarButtonSpec("btn_reset_password", "Reset Password"),
                ToolbarButtonSpec("btn_toggle_active", "Toggle Active"),
                ToolbarButtonSpec("btn_refresh", CFG.REFRESH_BUTTON_LABEL),
            ),
        )

        self.table = build_admin_table(
            headers=("Username", "Display Name", "Email", "Active", "Roles"),
            resize_modes=(
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
                QHeaderView.Stretch,
                QHeaderView.ResizeToContents,
                QHeaderView.Stretch,
            ),
        )
        layout.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(
            make_guarded_slot(self, title="Users", callback=self.reload_users)
        )
        self.btn_new_user.clicked.connect(
            make_guarded_slot(self, title="Users", callback=self.create_user)
        )
        self.btn_edit_user.clicked.connect(
            make_guarded_slot(self, title="Users", callback=self.edit_user)
        )
        self.btn_assign_role.clicked.connect(
            make_guarded_slot(self, title="Users", callback=self.assign_role)
        )
        self.btn_revoke_role.clicked.connect(
            make_guarded_slot(self, title="Users", callback=self.revoke_role)
        )
        self.btn_reset_password.clicked.connect(
            make_guarded_slot(self, title="Users", callback=self.reset_password)
        )
        self.btn_toggle_active.clicked.connect(
            make_guarded_slot(self, title="Users", callback=self.toggle_active)
        )
        self.table.itemSelectionChanged.connect(self._sync_actions)
        apply_permission_hint(
            self.btn_new_user,
            allowed=self._can_manage_users,
            missing_permission="auth.manage",
        )
        apply_permission_hint(
            self.btn_edit_user,
            allowed=self._can_manage_users,
            missing_permission="auth.manage",
        )
        apply_permission_hint(
            self.btn_assign_role,
            allowed=self._can_manage_users,
            missing_permission="auth.manage",
        )
        apply_permission_hint(
            self.btn_revoke_role,
            allowed=self._can_manage_users,
            missing_permission="auth.manage",
        )
        apply_permission_hint(
            self.btn_reset_password,
            allowed=self._can_manage_users,
            missing_permission="auth.manage",
        )
        apply_permission_hint(
            self.btn_toggle_active,
            allowed=self._can_manage_users,
            missing_permission="auth.manage",
        )
        self._sync_actions()

    def reload_users(self) -> None:
        try:
            users_result = self._platform_user_api.list_users()
            roles_result = self._platform_user_api.list_roles()
        except Exception as exc:
            QMessageBox.critical(self, "Users", f"Failed to load users: {exc}")
            self._rows = []
            self._roles = []
            self.table.setRowCount(0)
            self._update_header_badges([])
            self._sync_actions()
            return
        if not users_result.ok or users_result.data is None:
            self._show_api_error(users_result.error)
            self._rows = []
        else:
            self._rows = list(users_result.data)
        if not roles_result.ok or roles_result.data is None:
            self._show_api_error(roles_result.error)
            self._roles = []
        else:
            self._roles = list(roles_result.data)
        if not self._rows and (not users_result.ok or users_result.data is None):
            self.table.setRowCount(0)
            self._update_header_badges([])
            self._sync_actions()
            return
        self.table.setRowCount(len(self._rows))
        for row, user in enumerate(self._rows):
            values = (
                user.username,
                user.display_name or "",
                user.email or "",
                "Yes" if user.is_active else "No",
                ", ".join(sorted(user.role_names)) or "-",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, user.id)
        self.table.clearSelection()
        self._update_header_badges(self._rows)
        self._sync_actions()

    def _selected_user(self) -> UserDto | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        user_id = item.data(Qt.UserRole)
        for user in self._rows:
            if user.id == user_id:
                return user
        return None

    def create_user(self) -> None:
        dlg = UserCreateDialog(role_names=sorted(role.name for role in self._roles), parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                result = self._platform_user_api.create_user(
                    UserCreateCommand(
                        username=dlg.username,
                        password=dlg.password,
                        display_name=dlg.display_name,
                        email=dlg.email,
                        role_names=(dlg.role_name,),
                    )
                )
            except Exception as exc:
                QMessageBox.critical(self, "Users", f"Failed to create user: {exc}")
                return
            if not result.ok:
                self._show_api_error(result.error)
                if result.error is not None and result.error.category in {"validation", "conflict"}:
                    continue
                return
            break
        self.reload_users()

    def edit_user(self) -> None:
        user = self._selected_user()
        if not user:
            QMessageBox.information(self, "Users", "Please select a user.")
            return

        dlg = UserEditDialog(
            username=user.username,
            display_name=user.display_name,
            email=user.email,
            parent=self,
        )
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                result = self._platform_user_api.update_user(
                    UserUpdateCommand(
                        user_id=user.id,
                        username=dlg.username,
                        display_name=dlg.display_name,
                        email=dlg.email,
                    )
                )
            except Exception as exc:
                QMessageBox.critical(self, "Users", f"Failed to edit user: {exc}")
                return
            if not result.ok:
                self._show_api_error(result.error)
                if result.error is not None and result.error.category == "validation":
                    continue
                return
            break
        self.reload_users()

    def assign_role(self) -> None:
        user = self._selected_user()
        if not user:
            return
        role_names = [role.name for role in self._roles]
        role_name, ok = QInputDialog.getItem(
            self,
            "Assign Role",
            f"Role for '{user.username}':",
            sorted(role_names),
            editable=False,
        )
        if not ok:
            return
        try:
            result = self._platform_user_api.assign_role(user.id, role_name)
        except Exception as exc:
            QMessageBox.critical(self, "Users", f"Failed to assign role: {exc}")
            return
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_users()

    def revoke_role(self) -> None:
        user = self._selected_user()
        if not user:
            return
        user_roles = sorted(user.role_names)
        if not user_roles:
            QMessageBox.information(self, "Users", "User has no roles to revoke.")
            return
        role_name, ok = QInputDialog.getItem(
            self,
            "Revoke Role",
            f"Role to revoke from '{user.username}':",
            user_roles,
            editable=False,
        )
        if not ok:
            return
        try:
            result = self._platform_user_api.revoke_role(user.id, role_name)
        except Exception as exc:
            QMessageBox.critical(self, "Users", f"Failed to revoke role: {exc}")
            return
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_users()

    def toggle_active(self) -> None:
        user = self._selected_user()
        if not user:
            return
        try:
            result = self._platform_user_api.set_user_active(user.id, not user.is_active)
        except Exception as exc:
            QMessageBox.critical(self, "Users", f"Failed to update user: {exc}")
            return
        if not result.ok:
            self._show_api_error(result.error)
            return
        self.reload_users()

    def reset_password(self) -> None:
        user = self._selected_user()
        if not user:
            return
        dlg = PasswordResetDialog(username=user.username, parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            new_password = dlg.password
            try:
                result = self._platform_user_api.reset_password(
                    UserPasswordResetCommand(
                        user_id=user.id,
                        new_password=new_password,
                    )
                )
            except Exception as exc:
                QMessageBox.critical(self, "Users", f"Failed to reset password: {exc}")
                return
            if not result.ok:
                self._show_api_error(result.error)
                if result.error is not None and result.error.category == "validation":
                    continue
                return
            QMessageBox.information(self, "Users", f"Password reset for '{user.username}'.")
            return

    def _sync_actions(self) -> None:
        has_user = self._selected_user() is not None
        self.btn_new_user.setEnabled(self._can_manage_users)
        self.btn_edit_user.setEnabled(self._can_manage_users and has_user)
        self.btn_assign_role.setEnabled(self._can_manage_users and has_user)
        self.btn_revoke_role.setEnabled(self._can_manage_users and has_user)
        self.btn_reset_password.setEnabled(self._can_manage_users and has_user)
        self.btn_toggle_active.setEnabled(self._can_manage_users and has_user)

    def _update_header_badges(self, rows: list[UserDto]) -> None:
        active_count = sum(1 for row in rows if row.is_active)
        self.user_count_badge.setText(f"{len(rows)} users")
        self.user_active_badge.setText(f"{active_count} active")

    def _show_api_error(self, error: DesktopApiError | None) -> None:
        message = error.message if error is not None else "The platform user API did not return a result."
        QMessageBox.warning(self, "Users", message)


__all__ = ["UserAdminTab"]
