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

from core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from core.models import UserAccount
from core.services.auth import AuthService
from ui.admin.user_dialog import PasswordResetDialog, UserCreateDialog
from ui.styles.style_utils import style_table
from ui.styles.ui_config import UIConfig as CFG


class UserAdminTab(QWidget):
    def __init__(self, auth_service: AuthService, parent: QWidget | None = None):
        super().__init__(parent)
        self._auth_service = auth_service
        self._rows: list[UserAccount] = []
        self._setup_ui()
        self.reload_users()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(CFG.SPACING_MD)
        layout.setContentsMargins(CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD, CFG.MARGIN_MD)

        title = QLabel("User Administration")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Manage user accounts, roles, and active status.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        toolbar = QHBoxLayout()
        self.btn_refresh = QPushButton(CFG.REFRESH_BUTTON_LABEL)
        self.btn_new_user = QPushButton("New User")
        self.btn_assign_role = QPushButton("Assign Role")
        self.btn_revoke_role = QPushButton("Revoke Role")
        self.btn_reset_password = QPushButton("Reset Password")
        self.btn_toggle_active = QPushButton("Toggle Active")
        for btn in (
            self.btn_refresh,
            self.btn_new_user,
            self.btn_assign_role,
            self.btn_revoke_role,
            self.btn_reset_password,
            self.btn_toggle_active,
        ):
            btn.setFixedHeight(CFG.BUTTON_HEIGHT)
            btn.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        toolbar.addWidget(self.btn_refresh)
        toolbar.addWidget(self.btn_new_user)
        toolbar.addWidget(self.btn_assign_role)
        toolbar.addWidget(self.btn_revoke_role)
        toolbar.addWidget(self.btn_reset_password)
        toolbar.addWidget(self.btn_toggle_active)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Username", "Display Name", "Email", "Active", "Roles"])
        style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)

        self.btn_refresh.clicked.connect(self.reload_users)
        self.btn_new_user.clicked.connect(self.create_user)
        self.btn_assign_role.clicked.connect(self.assign_role)
        self.btn_revoke_role.clicked.connect(self.revoke_role)
        self.btn_reset_password.clicked.connect(self.reset_password)
        self.btn_toggle_active.clicked.connect(self.toggle_active)
        self.table.itemSelectionChanged.connect(self._sync_actions)
        self._sync_actions()

    def reload_users(self) -> None:
        role_cache: dict[str, set[str]] = {}
        try:
            self._rows = self._auth_service.list_users()
            for user in self._rows:
                role_cache[user.id] = self._auth_service.get_user_role_names(user.id)
        except BusinessRuleError as exc:
            QMessageBox.warning(self, "Users", str(exc))
            self._rows = []
            self.table.setRowCount(0)
            self._sync_actions()
            return
        except Exception as exc:
            QMessageBox.critical(self, "Users", f"Failed to load users: {exc}")
            self._rows = []
            self.table.setRowCount(0)
            self._sync_actions()
            return
        self.table.setRowCount(len(self._rows))
        for row, user in enumerate(self._rows):
            values = (
                user.username,
                user.display_name or "",
                user.email or "",
                "Yes" if user.is_active else "No",
                ", ".join(sorted(role_cache[user.id])) or "-",
            )
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 3:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
            self.table.item(row, 0).setData(Qt.UserRole, user.id)
        self.table.clearSelection()
        self._sync_actions()

    def _selected_user(self) -> UserAccount | None:
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
        try:
            role_names = [role.name for role in self._auth_service.list_roles()]
        except (ValidationError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Users", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Users", f"Failed to load roles: {exc}")
            return

        dlg = UserCreateDialog(role_names=sorted(role_names), parent=self)
        while True:
            if dlg.exec() != QDialog.Accepted:
                return
            try:
                self._auth_service.register_user(
                    username=dlg.username,
                    raw_password=dlg.password,
                    display_name=dlg.display_name,
                    email=dlg.email,
                    role_names=[dlg.role_name],
                )
            except ValidationError as exc:
                QMessageBox.warning(self, "Users", str(exc))
                continue
            except BusinessRuleError as exc:
                QMessageBox.warning(self, "Users", str(exc))
                return
            except Exception as exc:
                QMessageBox.critical(self, "Users", f"Failed to create user: {exc}")
                return
            break
        self.reload_users()

    def assign_role(self) -> None:
        user = self._selected_user()
        if not user:
            return
        role_names = [role.name for role in self._auth_service.list_roles()]
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
            self._auth_service.assign_role(user.id, role_name)
        except (ValidationError, NotFoundError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Users", str(exc))
            return
        self.reload_users()

    def revoke_role(self) -> None:
        user = self._selected_user()
        if not user:
            return
        user_roles = sorted(self._auth_service.get_user_role_names(user.id))
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
            self._auth_service.revoke_role(user.id, role_name)
        except (ValidationError, NotFoundError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Users", str(exc))
            return
        self.reload_users()

    def toggle_active(self) -> None:
        user = self._selected_user()
        if not user:
            return
        try:
            self._auth_service.set_user_active(user.id, not user.is_active)
        except (NotFoundError, BusinessRuleError) as exc:
            QMessageBox.warning(self, "Users", str(exc))
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
                self._auth_service.reset_user_password(user.id, new_password)
            except ValidationError as exc:
                QMessageBox.warning(self, "Users", str(exc))
                continue
            except (NotFoundError, BusinessRuleError) as exc:
                QMessageBox.warning(self, "Users", str(exc))
                return
            except Exception as exc:
                QMessageBox.critical(self, "Users", f"Failed to reset password: {exc}")
                return
            QMessageBox.information(self, "Users", f"Password reset for '{user.username}'.")
            return

    def _sync_actions(self) -> None:
        has_user = self._selected_user() is not None
        self.btn_assign_role.setEnabled(has_user)
        self.btn_revoke_role.setEnabled(has_user)
        self.btn_reset_password.setEnabled(has_user)
        self.btn_toggle_active.setEnabled(has_user)


__all__ = ["UserAdminTab"]
