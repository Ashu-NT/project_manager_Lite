from __future__ import annotations

import re

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from ui.styles.ui_config import UIConfig as CFG


_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def _set_password_fields_visibility(
    *,
    visible: bool,
    password_input: QLineEdit,
    confirm_password_input: QLineEdit,
    toggle_button: QPushButton,
) -> None:
    echo_mode = QLineEdit.Normal if visible else QLineEdit.Password
    password_input.setEchoMode(echo_mode)
    confirm_password_input.setEchoMode(echo_mode)
    toggle_button.setText("Hide" if visible else "Show")


def _apply_password_strength(label: QLabel, password: str) -> None:
    strength, color = _password_strength_ui(password)
    label.setText(f"Strength: {strength}")
    label.setStyleSheet(f"color: {color}; font-size: 9pt;")


class UserCreateDialog(QDialog):
    def __init__(self, role_names: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create User")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG)
        root.setSpacing(CFG.SPACING_MD)

        form = QFormLayout()
        form.setSpacing(CFG.SPACING_SM)
        self.username_input = QLineEdit()
        self.display_name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.btn_toggle_password = QPushButton("Show")
        self.btn_toggle_password.setCheckable(True)
        self.btn_toggle_password.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_toggle_password.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.password_strength_label = QLabel("Strength: weak")
        self.password_strength_label.setStyleSheet(
            f"color: {CFG.COLOR_DANGER}; font-size: 9pt;"
        )
        self.role_combo = QComboBox()
        for role_name in role_names:
            self.role_combo.addItem(role_name, userData=role_name)
        password_row = QHBoxLayout()
        password_row.setContentsMargins(0, 0, 0, 0)
        password_row.setSpacing(CFG.SPACING_XS)
        password_row.addWidget(self.password_input, 1)
        password_row.addWidget(self.btn_toggle_password)
        form.addRow("Username:", self.username_input)
        form.addRow("Display Name:", self.display_name_input)
        form.addRow("Email:", self.email_input)
        form.addRow("Password:", password_row)
        form.addRow("Confirm Password:", self.confirm_password_input)
        form.addRow("Initial Role:", self.role_combo)
        root.addLayout(form)
        root.addWidget(self.password_strength_label)

        row = QHBoxLayout()
        row.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Create")
        self.btn_cancel.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_save.setFixedHeight(CFG.BUTTON_HEIGHT)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_save)
        root.addLayout(row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._validate_and_accept)
        self.btn_toggle_password.toggled.connect(self._toggle_password_visibility)
        self.password_input.textChanged.connect(self._update_password_strength)
        self._update_password_strength("")

    def _validate_and_accept(self) -> None:
        if not self.username:
            QMessageBox.warning(self, "Create User", "Username is required.")
            return
        if not self.password:
            QMessageBox.warning(self, "Create User", "Password is required.")
            return
        if not self.passwords_match:
            QMessageBox.warning(
                self,
                "Create User",
                "Password and confirm password must match.",
            )
            return
        if self.email and not _EMAIL_RE.match(self.email):
            QMessageBox.warning(self, "Create User", "Invalid email format.")
            return
        self.accept()

    def _toggle_password_visibility(self, visible: bool) -> None:
        _set_password_fields_visibility(
            visible=visible,
            password_input=self.password_input,
            confirm_password_input=self.confirm_password_input,
            toggle_button=self.btn_toggle_password,
        )

    def _update_password_strength(self, password: str) -> None:
        _apply_password_strength(self.password_strength_label, password)

    @property
    def username(self) -> str:
        return self.username_input.text().strip()

    @property
    def display_name(self) -> str | None:
        value = self.display_name_input.text().strip()
        return value or None

    @property
    def email(self) -> str | None:
        value = self.email_input.text().strip()
        return value or None

    @property
    def password(self) -> str:
        return self.password_input.text()

    @property
    def confirm_password(self) -> str:
        return self.confirm_password_input.text()

    @property
    def role_name(self) -> str:
        return str(self.role_combo.currentData() or "viewer")

    @property
    def passwords_match(self) -> bool:
        return self.password == self.confirm_password


class PasswordResetDialog(QDialog):
    def __init__(self, username: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG)
        root.setSpacing(CFG.SPACING_MD)

        title = QLabel(f"Reset password for '{username}'")
        title.setStyleSheet(CFG.INFO_TEXT_STYLE)
        title.setWordWrap(True)
        root.addWidget(title)

        form = QFormLayout()
        form.setSpacing(CFG.SPACING_SM)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.btn_toggle_password = QPushButton("Show")
        self.btn_toggle_password.setCheckable(True)
        self.btn_toggle_password.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_toggle_password.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        self.password_strength_label = QLabel("Strength: weak")
        self.password_strength_label.setStyleSheet(
            f"color: {CFG.COLOR_DANGER}; font-size: 9pt;"
        )
        password_row = QHBoxLayout()
        password_row.setContentsMargins(0, 0, 0, 0)
        password_row.setSpacing(CFG.SPACING_XS)
        password_row.addWidget(self.password_input, 1)
        password_row.addWidget(self.btn_toggle_password)
        form.addRow("New Password:", password_row)
        form.addRow("Confirm Password:", self.confirm_password_input)
        root.addLayout(form)
        root.addWidget(self.password_strength_label)

        row = QHBoxLayout()
        row.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Reset")
        self.btn_cancel.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_save.setFixedHeight(CFG.BUTTON_HEIGHT)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_save)
        root.addLayout(row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._validate_and_accept)
        self.btn_toggle_password.toggled.connect(self._toggle_password_visibility)
        self.password_input.textChanged.connect(self._update_password_strength)
        self._update_password_strength("")

    def _validate_and_accept(self) -> None:
        if not self.password:
            QMessageBox.warning(self, "Reset Password", "Password is required.")
            return
        if not self.passwords_match:
            QMessageBox.warning(
                self,
                "Reset Password",
                "Password and confirm password must match.",
            )
            return
        self.accept()

    def _toggle_password_visibility(self, visible: bool) -> None:
        _set_password_fields_visibility(
            visible=visible,
            password_input=self.password_input,
            confirm_password_input=self.confirm_password_input,
            toggle_button=self.btn_toggle_password,
        )

    def _update_password_strength(self, password: str) -> None:
        _apply_password_strength(self.password_strength_label, password)

    @property
    def password(self) -> str:
        return self.password_input.text()

    @property
    def confirm_password(self) -> str:
        return self.confirm_password_input.text()

    @property
    def passwords_match(self) -> bool:
        return self.password == self.confirm_password


class UserEditDialog(QDialog):
    def __init__(
        self,
        *,
        username: str,
        display_name: str | None,
        email: str | None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Edit User")
        self.setMinimumWidth(420)

        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG)
        root.setSpacing(CFG.SPACING_MD)

        form = QFormLayout()
        form.setSpacing(CFG.SPACING_SM)
        self.username_input = QLineEdit()
        self.display_name_input = QLineEdit()
        self.email_input = QLineEdit()
        self.username_input.setText((username or "").strip())
        self.display_name_input.setText((display_name or "").strip())
        self.email_input.setText((email or "").strip())
        form.addRow("Username:", self.username_input)
        form.addRow("Display Name:", self.display_name_input)
        form.addRow("Email:", self.email_input)
        root.addLayout(form)

        row = QHBoxLayout()
        row.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_save = QPushButton("Save")
        self.btn_cancel.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_save.setFixedHeight(CFG.BUTTON_HEIGHT)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_save)
        root.addLayout(row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_save.clicked.connect(self._validate_and_accept)

    def _validate_and_accept(self) -> None:
        if not self.username:
            QMessageBox.warning(self, "Edit User", "Username is required.")
            return
        if self.email and not _EMAIL_RE.match(self.email):
            QMessageBox.warning(self, "Edit User", "Invalid email format.")
            return
        self.accept()

    @property
    def username(self) -> str:
        return self.username_input.text().strip()

    @property
    def display_name(self) -> str | None:
        value = self.display_name_input.text().strip()
        return value or None

    @property
    def email(self) -> str | None:
        value = self.email_input.text().strip()
        return value or None


def _password_strength_ui(password: str) -> tuple[str, str]:
    score = 0
    pwd = password or ""
    if len(pwd) >= 8:
        score += 1
    if any(ch.islower() for ch in pwd):
        score += 1
    if any(ch.isupper() for ch in pwd):
        score += 1
    if any(ch.isdigit() for ch in pwd):
        score += 1
    if len(pwd) >= 12:
        score += 1

    if score <= 2:
        return "weak", CFG.COLOR_DANGER
    if score <= 4:
        return "medium", CFG.COLOR_WARNING
    return "strong", CFG.COLOR_SUCCESS


__all__ = ["PasswordResetDialog", "UserCreateDialog", "UserEditDialog"]
