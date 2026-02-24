from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings


class MainWindowSettingsStore:
    """Adapter around QSettings for persisted main-window UI state."""

    ORG_NAME = "TECHASH"
    APP_NAME = "ProjectManagerLite"

    _KEY_THEME_MODE = "ui/theme_mode"
    _KEY_TAB_INDEX = "ui/current_tab_index"
    _KEY_GEOMETRY = "ui/main_window_geometry"

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

