from __future__ import annotations

import time
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QSettings

from src.infra.platform.app_settings import AppSettingsStore


def make_settings_store(root: Path, *, prefix: str) -> AppSettingsStore:
    settings_path = root / f"{prefix}-{uuid4().hex}.ini"
    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.clear()
    return AppSettingsStore(settings)


def login_as(services, username: str, password: str):
    user_session = services["user_session"]
    user = services["authentication"].authenticate(username, password)
    principal = services["principal_builder"].build(user)
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
    services["user_registration"].register_user(
        username=username,
        raw_password=password,
        role_names=role_names,
    )
    return login_as(services, username, password)


def wait_until(qapp, predicate, *, timeout_ms: int = 3000, step_ms: int = 25) -> None:
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        qapp.processEvents()
        if predicate():
            return
        time.sleep(step_ms / 1000.0)
    qapp.processEvents()
    assert predicate()

