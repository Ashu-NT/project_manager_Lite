from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

from ui.settings.main_window_store import MainWindowSettingsStore


def _store_with_ini(tmp_path):
    ini_path = tmp_path / "ui_settings.ini"
    settings = QSettings(str(ini_path), QSettings.IniFormat)
    settings.clear()
    settings.sync()
    return MainWindowSettingsStore(settings), settings


def test_main_window_settings_store_round_trip(tmp_path):
    store, _settings = _store_with_ini(tmp_path)
    geometry = QByteArray(b"\x01\x02\x03\x04")

    store.save_theme_mode("dark")
    store.save_governance_mode("required")
    store.save_tab_index(5)
    store.save_geometry(geometry)

    assert store.load_theme_mode(default_mode="light") == "dark"
    assert store.load_governance_mode(default_mode="off") == "required"
    assert store.load_tab_index(default_index=0) == 5
    loaded_geometry = store.load_geometry()
    assert loaded_geometry is not None
    assert bytes(loaded_geometry) == bytes(geometry)


def test_main_window_settings_store_normalizes_invalid_values(tmp_path):
    store, settings = _store_with_ini(tmp_path)
    settings.setValue("ui/theme_mode", "INVALID")
    settings.setValue("governance/mode", "INVALID")
    settings.setValue("ui/current_tab_index", "-3")
    settings.sync()

    assert store.load_theme_mode(default_mode="dark") == "dark"
    assert store.load_governance_mode(default_mode="required") == "required"
    assert store.load_tab_index(default_index=2) == 0


def test_main_qt_loads_theme_from_settings_before_app_style():
    text = (Path(__file__).resolve().parents[1] / "main_qt.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert "MainWindowSettingsStore" in text
    assert "load_theme_mode" in text
    assert "load_governance_mode" in text
    assert "apply_app_style(app, mode=startup_theme)" in text


def test_main_window_persists_and_restores_ui_state_with_store():
    text = (Path(__file__).resolve().parents[1] / "ui" / "main_window.py").read_text(
        encoding="utf-8",
        errors="ignore",
    )
    assert "self._settings_store = MainWindowSettingsStore()" in text
    assert "def _restore_persisted_state" in text
    assert "def _on_tab_changed" in text
    assert "def closeEvent" in text
