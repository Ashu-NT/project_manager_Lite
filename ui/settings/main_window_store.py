from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings

from infra.update import default_update_manifest_source


class MainWindowSettingsStore:
    """Adapter around QSettings for persisted main-window UI state."""

    ORG_NAME = "TECHASH"
    APP_NAME = "ProjectManagerLite"

    _KEY_THEME_MODE = "ui/theme_mode"
    _KEY_TAB_INDEX = "ui/current_tab_index"
    _KEY_GEOMETRY = "ui/main_window_geometry"
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

    def save_theme_mode(self, mode: str) -> None:
        normalized = (mode or "light").strip().lower()
        self._settings.setValue(self._KEY_THEME_MODE, "dark" if normalized == "dark" else "light")
        self._settings.sync()

    def load_governance_mode(self, default_mode: str = "off") -> str:
        default = (default_mode or "off").strip().lower()
        if default not in {"off", "required"}:
            default = "off"
        raw = str(self._settings.value(self._KEY_GOVERNANCE_MODE, default)).strip().lower()
        return raw if raw in {"off", "required"} else default

    def save_governance_mode(self, mode: str) -> None:
        normalized = (mode or "off").strip().lower()
        value = "required" if normalized == "required" else "off"
        self._settings.setValue(self._KEY_GOVERNANCE_MODE, value)
        self._settings.sync()

    def load_update_channel(self, default_channel: str = "stable") -> str:
        default = (default_channel or "stable").strip().lower()
        if default not in {"stable", "beta"}:
            default = "stable"
        raw = str(self._settings.value(self._KEY_UPDATE_CHANNEL, default)).strip().lower()
        return raw if raw in {"stable", "beta"} else default

    def save_update_channel(self, channel: str) -> None:
        normalized = (channel or "stable").strip().lower()
        value = "beta" if normalized == "beta" else "stable"
        self._settings.setValue(self._KEY_UPDATE_CHANNEL, value)
        self._settings.sync()

    def load_update_auto_check(self, default_enabled: bool = False) -> bool:
        raw = self._settings.value(self._KEY_UPDATE_AUTO_CHECK, default_enabled)
        if isinstance(raw, bool):
            return raw
        text = str(raw).strip().lower()
        return text in {"1", "true", "yes", "on"}

    def save_update_auto_check(self, enabled: bool) -> None:
        self._settings.setValue(self._KEY_UPDATE_AUTO_CHECK, bool(enabled))
        self._settings.sync()

    def load_update_manifest_url(self, default_url: str = "") -> str:
        fallback = (default_url or default_update_manifest_source()).strip()
        raw = self._settings.value(self._KEY_UPDATE_MANIFEST_URL, fallback)
        value = str(raw or "").strip()
        return value or fallback

    def save_update_manifest_url(self, url: str) -> None:
        self._settings.setValue(self._KEY_UPDATE_MANIFEST_URL, (url or "").strip())
        self._settings.sync()

    def load_tab_index(self, default_index: int = 0) -> int:
        raw = self._settings.value(self._KEY_TAB_INDEX, default_index)
        try:
            idx = int(raw)
        except (TypeError, ValueError):
            idx = default_index
        return max(0, idx)

    def save_tab_index(self, index: int) -> None:
        self._settings.setValue(self._KEY_TAB_INDEX, max(0, int(index)))
        self._settings.sync()

    def load_geometry(self) -> QByteArray | None:
        raw = self._settings.value(self._KEY_GEOMETRY)
        if isinstance(raw, QByteArray) and not raw.isEmpty():
            return raw
        return None

    def save_geometry(self, geometry: QByteArray | None) -> None:
        if geometry is not None and not geometry.isEmpty():
            self._settings.setValue(self._KEY_GEOMETRY, geometry)
            self._settings.sync()
