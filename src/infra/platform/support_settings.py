from __future__ import annotations

from PySide6.QtCore import QSettings

from src.core.platform.application.support.dto.commands.settings import (
    SupportSettingsUpdateCommand,
)
from src.infra.platform.update import default_update_manifest_source


class SupportSettingsStore:
    ORG_NAME = "TECHASH"
    APP_NAME = "ProjectManagerLite"

    _KEY_THEME_MODE = "ui/theme_mode"
    _KEY_GOVERNANCE_MODE = "governance/mode"
    _KEY_UPDATE_CHANNEL = "updates/channel"
    _KEY_UPDATE_AUTO_CHECK = "updates/auto_check"
    _KEY_UPDATE_MANIFEST_URL = "updates/manifest_url"

    def __init__(self, settings: QSettings | None = None) -> None:
        self._settings = settings or QSettings(self.ORG_NAME, self.APP_NAME)

    def load_theme_mode(self, default_mode: str = "light") -> str:
        default = (default_mode or "light").strip().lower()
        if default not in {"light", "dark"}:
            default = "light"
        raw = str(self._settings.value(self._KEY_THEME_MODE, default)).strip().lower()
        return raw if raw in {"light", "dark"} else default

    def load_governance_mode(self, default_mode: str = "off") -> str:
        default = (default_mode or "off").strip().lower()
        if default not in {"off", "required"}:
            default = "off"
        raw = str(self._settings.value(self._KEY_GOVERNANCE_MODE, default)).strip().lower()
        return raw if raw in {"off", "required"} else default

    def load_update_channel(self, default_channel: str = "stable") -> str:
        default = (default_channel or "stable").strip().lower()
        if default not in {"stable", "beta"}:
            default = "stable"
        raw = str(self._settings.value(self._KEY_UPDATE_CHANNEL, default)).strip().lower()
        return raw if raw in {"stable", "beta"} else default

    def save_update_channel(self, channel: str) -> None:
        normalized = (channel or "stable").strip().lower()
        self._settings.setValue(self._KEY_UPDATE_CHANNEL, "beta" if normalized == "beta" else "stable")
        self._settings.sync()

    def load_update_auto_check(self, default_enabled: bool = False) -> bool:
        raw = self._settings.value(self._KEY_UPDATE_AUTO_CHECK, default_enabled)
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {"1", "true", "yes", "on"}

    def save_update_auto_check(self, enabled: bool) -> None:
        self._settings.setValue(self._KEY_UPDATE_AUTO_CHECK, bool(enabled))
        self._settings.sync()

    def load_update_manifest_source(self, default_source: str = "") -> str:
        fallback = (default_source or default_update_manifest_source()).strip()
        raw = self._settings.value(self._KEY_UPDATE_MANIFEST_URL, fallback)
        value = str(raw or "").strip()
        return value or fallback

    def save_update_manifest_source(self, source: str) -> None:
        self._settings.setValue(self._KEY_UPDATE_MANIFEST_URL, (source or "").strip())
        self._settings.sync()

    def save_settings(self, command: SupportSettingsUpdateCommand) -> None:
        self.save_update_channel(command.update_channel)
        self.save_update_auto_check(command.update_auto_check)
        manifest_source = (command.update_manifest_source or "").strip() or default_update_manifest_source()
        self.save_update_manifest_source(manifest_source)
