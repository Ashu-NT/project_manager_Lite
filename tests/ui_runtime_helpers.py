from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QSettings

from ui.platform.settings.main_window_store import MainWindowSettingsStore


def make_settings_store(root: Path, *, prefix: str) -> MainWindowSettingsStore:
    settings_path = root / f"{prefix}-{uuid4().hex}.ini"
    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.clear()
    return MainWindowSettingsStore(settings)


def login_as(services, username: str, password: str):
    auth = services["auth_service"]
    user_session = services["user_session"]
    user = auth.authenticate(username, password)
    principal = auth.build_principal(user)
    user_session.set_principal(principal)
    return principal


def register_and_login(
    services,
    *,
    username_prefix: str,
    password: str = "StrongPass123",
    role_names: tuple[str, ...] = ("viewer",),
):
    username = f"{username_prefix}-{uuid4().hex[:8]}"
    services["auth_service"].register_user(
        username=username,
        raw_password=password,
        role_names=role_names,
    )
    return login_as(services, username, password)
