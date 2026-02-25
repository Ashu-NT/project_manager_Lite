from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from core.exceptions import ValidationError
from core.services.auth import AuthService, UserSessionContext, UserSessionPrincipal
from ui.styles.ui_config import UIConfig as CFG


class LoginDialog(QDialog):
    def __init__(
        self,
        auth_service: AuthService,
        user_session: UserSessionContext,
        parent=None,
    ):
        super().__init__(parent)
        self._auth_service = auth_service
        self._user_session = user_session
        self._principal: UserSessionPrincipal | None = None

        self.setWindowTitle("Sign In")
        self.setMinimumWidth(420)
        self._build_ui()

    @property
    def principal(self) -> UserSessionPrincipal | None:
        return self._principal

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG, CFG.MARGIN_LG)
        root.setSpacing(CFG.SPACING_MD)

        title = QLabel("ProjectPulse Sign In")
        title.setStyleSheet(CFG.TITLE_LARGE_STYLE)
        subtitle = QLabel("Use your account credentials to access the workspace.")
        subtitle.setStyleSheet(CFG.INFO_TEXT_STYLE)
        subtitle.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(subtitle)

        form = QFormLayout()
        form.setSpacing(CFG.SPACING_SM)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setText("admin")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.btn_toggle_password = QPushButton("Show")
        self.btn_toggle_password.setCheckable(True)
        self.btn_toggle_password.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_toggle_password.setSizePolicy(CFG.BTN_FIXED_HEIGHT)
        password_row = QHBoxLayout()
        password_row.setContentsMargins(0, 0, 0, 0)
        password_row.setSpacing(CFG.SPACING_XS)
        password_row.addWidget(self.password_input, 1)
        password_row.addWidget(self.btn_toggle_password)
        form.addRow("Username:", self.username_input)
        form.addRow("Password:", password_row)
        root.addLayout(form)

        row = QHBoxLayout()
        row.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_sign_in = QPushButton("Sign In")
        self.btn_sign_in.setFixedHeight(CFG.BUTTON_HEIGHT)
        self.btn_cancel.setFixedHeight(CFG.BUTTON_HEIGHT)
        row.addWidget(self.btn_cancel)
        row.addWidget(self.btn_sign_in)
        root.addLayout(row)

        self.btn_cancel.clicked.connect(self.reject)
        self.btn_sign_in.clicked.connect(self._try_sign_in)
        self.btn_toggle_password.toggled.connect(self._toggle_password_visibility)
        self.password_input.returnPressed.connect(self._try_sign_in)
        self.username_input.returnPressed.connect(self._try_sign_in)

    def _toggle_password_visibility(self, visible: bool) -> None:
        self.password_input.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
        self.btn_toggle_password.setText("Hide" if visible else "Show")

    def _try_sign_in(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Sign In", "Username and password are required.")
            return
        try:
            user = self._auth_service.authenticate(username, password)
            principal = self._auth_service.build_principal(user)
        except ValidationError as exc:
            QMessageBox.warning(self, "Sign In failed", str(exc))
            return
        except Exception as exc:
            QMessageBox.critical(self, "Sign In failed", str(exc))
            return

        self._principal = principal
        self._user_session.set_principal(principal)
        self.accept()


__all__ = ["LoginDialog"]
