from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.core.platform.auth import AuthService, UserSessionContext
from src.core.platform.common.exceptions import ValidationError


@dataclass(frozen=True)
class LoginViewModel:
    title: str = "Sign in"
    username_label: str = "Username"
    password_label: str = "Password"
    submit_label: str = "Continue"
    username: str = ""
    password: str = ""
    error_message: str = ""
    is_busy: bool = False


class ShellLoginController(QObject):
    accepted = Signal()
    rejected = Signal()
    usernameChanged = Signal()
    passwordChanged = Signal()
    errorMessageChanged = Signal()
    isBusyChanged = Signal()
    isAuthenticatedChanged = Signal()

    def __init__(
        self,
        *,
        auth_service: AuthService,
        user_session: UserSessionContext,
        username: str = "admin",
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._user_session = user_session
        self._username = username
        self._password = ""
        self._error_message = ""
        self._is_busy = False
        self._is_authenticated = bool(user_session.is_authenticated())

    @Property(str, notify=usernameChanged)
    def username(self) -> str:
        return self._username

    @Property(str, notify=passwordChanged)
    def password(self) -> str:
        return self._password

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    @Property(bool, notify=isBusyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property(bool, notify=isAuthenticatedChanged)
    def isAuthenticated(self) -> bool:
        return self._is_authenticated

    @Slot(str)
    def setUsername(self, value: str) -> None:
        normalized = str(value or "")
        if normalized == self._username:
            return
        self._username = normalized
        self.usernameChanged.emit()

    @Slot(str)
    def setPassword(self, value: str) -> None:
        normalized = str(value or "")
        if normalized == self._password:
            return
        self._password = normalized
        self.passwordChanged.emit()

    @Slot()
    def signIn(self) -> None:
        username = self._username.strip().lower()
        password = self._password
        if not username or not password:
            self._set_error_message("Username and password are required.")
            return
        self._set_is_busy(True)
        self._set_error_message("")
        try:
            user = self._auth_service.authenticate(username, password)
            principal = self._auth_service.build_principal(user)
        except ValidationError as exc:
            self._set_error_message(str(exc))
            self._set_is_busy(False)
            return
        except Exception as exc:  # noqa: BLE001
            self._set_error_message(str(exc))
            self._set_is_busy(False)
            return

        self._user_session.set_principal(principal)
        self._set_is_authenticated(True)
        self._set_password("")
        self._set_is_busy(False)
        self.accepted.emit()

    @Slot()
    def cancel(self) -> None:
        self.rejected.emit()

    def _set_password(self, value: str) -> None:
        if value == self._password:
            return
        self._password = value
        self.passwordChanged.emit()

    def _set_error_message(self, value: str) -> None:
        if value == self._error_message:
            return
        self._error_message = value
        self.errorMessageChanged.emit()

    def _set_is_busy(self, value: bool) -> None:
        if value == self._is_busy:
            return
        self._is_busy = value
        self.isBusyChanged.emit()

    def _set_is_authenticated(self, value: bool) -> None:
        if value == self._is_authenticated:
            return
        self._is_authenticated = value
        self.isAuthenticatedChanged.emit()


__all__ = ["LoginViewModel", "ShellLoginController"]
