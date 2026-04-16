from __future__ import annotations

from PySide6.QtWidgets import QDialog, QWidget

from src.core.platform.auth import AuthService, UserSessionContext
from ui.platform.shared.auth.login_dialog import LoginDialog


def prompt_for_login(
    *,
    auth_service: AuthService,
    user_session: UserSessionContext,
    parent: QWidget | None = None,
) -> bool:
    dialog = LoginDialog(
        auth_service=auth_service,
        user_session=user_session,
        parent=parent,
    )
    return dialog.exec() == QDialog.Accepted


__all__ = ["prompt_for_login"]
