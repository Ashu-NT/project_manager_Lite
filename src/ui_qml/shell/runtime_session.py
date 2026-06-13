from __future__ import annotations

import logging
from collections.abc import Callable, Sequence

from PySide6.QtCore import QObject, QTimer, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication

from src.core.platform.auth import UserSessionContext
from src.ui_qml.shell.context import ShellContext, update_shell_runtime_state

logger = logging.getLogger(__name__)


class ShellRuntimeSessionController(QObject):
    sessionExpired = Signal()
    reauthenticated = Signal()

    def __init__(
        self,
        *,
        shell_context: ShellContext,
        user_session: UserSessionContext,
        login_prompt: Callable[[str | None], bool],
        refresh_callbacks: Sequence[Callable[[], None]] | None = None,
        quit_application: Callable[[], None] | None = None,
        poll_interval_ms: int = 30_000,
        app: QGuiApplication | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._shell_context = shell_context
        self._user_session = user_session
        self._login_prompt = login_prompt
        self._refresh_callbacks = tuple(refresh_callbacks or ())
        self._quit_application = quit_application or self._default_quit_application
        self._app = app or QGuiApplication.instance()
        self._poll_interval_ms = max(1_000, int(poll_interval_ms or 30_000))
        self._reauthentication_in_progress = False
        self._last_authenticated = bool(self._user_session.is_authenticated())
        self._last_username = self._current_username()

        self._timer = QTimer(self)
        self._timer.setInterval(self._poll_interval_ms)
        self._timer.timeout.connect(self.revalidateSession)

        if self._app is not None:
            self._app.applicationStateChanged.connect(self._on_application_state_changed)

    @Slot()
    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start()

    @Slot()
    def stop(self) -> None:
        if self._timer.isActive():
            self._timer.stop()

    @Slot()
    def revalidateSession(self) -> None:
        if self._reauthentication_in_progress:
            return
        principal = self._user_session.principal
        if principal is not None:
            self._last_username = str(principal.username or "").strip() or self._last_username
        is_authenticated = bool(self._user_session.is_authenticated())
        if is_authenticated:
            self._last_authenticated = True
            self._sync_shell_identity()
            return
        if not self._last_authenticated:
            return
        self._last_authenticated = False
        self._handle_session_expired()

    @Slot(int)
    def _on_application_state_changed(self, state: int) -> None:
        if state == int(Qt.ApplicationState.ApplicationActive):
            self.revalidateSession()

    def _handle_session_expired(self) -> None:
        self.sessionExpired.emit()
        self._reauthentication_in_progress = True
        try:
            accepted = bool(self._login_prompt(self._last_username or None))
        finally:
            self._reauthentication_in_progress = False
        if not accepted or not self._user_session.is_authenticated():
            logger.info("Runtime re-authentication declined or failed; exiting application.")
            self._quit_application()
            return
        self._last_authenticated = True
        self._last_username = self._current_username()
        self._sync_shell_identity()
        self._refresh_runtime_state()
        self._shell_context.reloadCurrentRoute()
        self.reauthenticated.emit()

    def _sync_shell_identity(self) -> None:
        principal = self._user_session.principal
        update_shell_runtime_state(
            self._shell_context,
            user_display_name=(
                principal.display_name or principal.username
                if principal is not None
                else ""
            ),
        )

    def _refresh_runtime_state(self) -> None:
        for refresh_callback in self._refresh_callbacks:
            try:
                refresh_callback()
            except Exception:
                logger.exception("Runtime workspace refresh failed after re-authentication.")

    def _current_username(self) -> str:
        principal = self._user_session.principal
        if principal is None:
            return ""
        return str(principal.username or "").strip()

    @staticmethod
    def _default_quit_application() -> None:
        app = QGuiApplication.instance()
        if app is not None:
            app.quit()


__all__ = ["ShellRuntimeSessionController"]
