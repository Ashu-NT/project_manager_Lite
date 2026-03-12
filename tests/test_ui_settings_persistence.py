from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

import main_qt
from ui.main_window import MainWindow
from ui.settings.main_window_store import MainWindowSettingsStore


def _store_with_ini(root: Path):
    ini_path = root / "ui_settings.ini"
    settings = QSettings(str(ini_path), QSettings.IniFormat)
    settings.clear()
    settings.sync()
    return MainWindowSettingsStore(settings), settings


def test_main_window_settings_store_round_trip(repo_workspace):
    store, _settings = _store_with_ini(repo_workspace)
    geometry = QByteArray(b"\x01\x02\x03\x04")
    views = {"Sprint View": {"query": "status:in_progress", "status": 2}}
    layout = {"show_kpi": True, "main_left_percent": 55}

    store.save_theme_mode("dark")
    store.save_governance_mode("required")
    store.save_update_channel("beta")
    store.save_update_auto_check(True)
    store.save_update_manifest_url("https://example.com/manifest.json")
    store.save_task_saved_views(views)
    store.save_dashboard_layout(layout)
    store.save_tab_index(5)
    store.save_geometry(geometry)

    assert store.load_theme_mode(default_mode="light") == "dark"
    assert store.load_governance_mode(default_mode="off") == "required"
    assert store.load_update_channel(default_channel="stable") == "beta"
    assert store.load_update_auto_check(default_enabled=False) is True
    assert store.load_update_manifest_url(default_url="") == "https://example.com/manifest.json"
    assert store.load_task_saved_views() == views
    assert store.load_dashboard_layout() == layout
    assert store.load_tab_index(default_index=0) == 5
    loaded_geometry = store.load_geometry()
    assert loaded_geometry is not None
    assert bytes(loaded_geometry) == bytes(geometry)


def test_main_window_settings_store_normalizes_invalid_values(repo_workspace):
    store, settings = _store_with_ini(repo_workspace)
    settings.setValue("ui/theme_mode", "INVALID")
    settings.setValue("governance/mode", "INVALID")
    settings.setValue("updates/channel", "INVALID")
    settings.setValue("updates/auto_check", "invalid")
    settings.setValue("ui/current_tab_index", "-3")
    settings.sync()

    assert store.load_theme_mode(default_mode="dark") == "dark"
    assert store.load_governance_mode(default_mode="required") == "required"
    assert store.load_update_channel(default_channel="stable") == "stable"
    assert store.load_update_auto_check(default_enabled=False) is False
    assert store.load_tab_index(default_index=2) == 0


def test_manifest_url_defaults_from_env_when_unset(repo_workspace, monkeypatch):
    monkeypatch.setenv("PM_UPDATE_MANIFEST_URL", "https://example.com/latest-manifest.json")
    store, settings = _store_with_ini(repo_workspace)
    settings.remove("updates/manifest_url")
    settings.sync()

    assert store.load_update_manifest_url(default_url="") == "https://example.com/latest-manifest.json"


def test_main_qt_loads_theme_from_settings_before_app_style(repo_workspace, services, monkeypatch):
    store, _settings = _store_with_ini(repo_workspace)
    store.save_theme_mode("dark")
    store.save_governance_mode("required")

    calls: list[tuple[str, object, object]] = []

    class _FakeApp:
        def __init__(self, _argv):
            calls.append(("app", None, None))

        def setWindowIcon(self, _icon):
            return None

        def setStyleSheet(self, _css):
            return None

        def setFont(self, _font):
            return None

        def exec(self):
            calls.append(("exec", None, None))
            return 0

    class _FakeMainWindow:
        def __init__(self, incoming_services):
            calls.append(
                (
                    "window",
                    incoming_services is services,
                    (
                        os.getenv("PM_THEME"),
                        os.getenv("PM_GOVERNANCE_MODE"),
                    ),
                )
            )

        def show(self):
            calls.append(("show", None, None))

    monkeypatch.setenv("PM_SKIP_LOGIN", "1")
    monkeypatch.setattr(main_qt, "QApplication", _FakeApp)
    monkeypatch.setattr(main_qt, "QIcon", lambda path: path)
    monkeypatch.setattr(main_qt, "QFont", lambda family, size: (family, size))
    monkeypatch.setattr(main_qt, "resource_path", lambda rel_path: rel_path)
    monkeypatch.setattr(main_qt, "setup_logging", lambda: None)
    monkeypatch.setattr(main_qt, "build_services", lambda: services)
    monkeypatch.setattr(main_qt, "MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(main_qt, "MainWindow", _FakeMainWindow)
    monkeypatch.setattr(main_qt.sys, "exit", lambda code: calls.append(("exit", code, None)))
    monkeypatch.setattr(
        "ui.styles.theme.apply_app_style",
        lambda _app, mode: calls.append(
            (
                "style",
                mode,
                (
                    os.getenv("PM_THEME"),
                    os.getenv("PM_GOVERNANCE_MODE"),
                ),
            )
        ),
    )

    main_qt.main()

    style_index = next(i for i, call in enumerate(calls) if call[0] == "style")
    window_index = next(i for i, call in enumerate(calls) if call[0] == "window")
    assert style_index < window_index
    assert calls[style_index] == ("style", "dark", ("dark", "required"))
    assert calls[window_index] == ("window", True, ("dark", "required"))


def test_main_qt_skip_login_does_not_bypass_unauthenticated_services(
    repo_workspace,
    anonymous_services,
    monkeypatch,
):
    store, _settings = _store_with_ini(repo_workspace)
    calls: list[tuple[str, object, object]] = []

    class _FakeApp:
        def __init__(self, _argv):
            calls.append(("app", None, None))

        def setWindowIcon(self, _icon):
            return None

        def setStyleSheet(self, _css):
            return None

        def setFont(self, _font):
            return None

        def exec(self):
            calls.append(("exec", None, None))
            return 0

    class _FakeLoginDialog:
        def __init__(self, auth_service, user_session):
            calls.append(("login", auth_service is anonymous_services["auth_service"], user_session.is_authenticated()))

        def exec(self):
            calls.append(("login-exec", None, None))
            return main_qt.QDialog.Rejected

    monkeypatch.setenv("PM_SKIP_LOGIN", "1")
    monkeypatch.setattr(main_qt, "QApplication", _FakeApp)
    monkeypatch.setattr(main_qt, "QIcon", lambda path: path)
    monkeypatch.setattr(main_qt, "QFont", lambda family, size: (family, size))
    monkeypatch.setattr(main_qt, "resource_path", lambda rel_path: rel_path)
    monkeypatch.setattr(main_qt, "setup_logging", lambda: None)
    monkeypatch.setattr(main_qt, "build_services", lambda: anonymous_services)
    monkeypatch.setattr(main_qt, "MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(main_qt, "LoginDialog", _FakeLoginDialog)
    monkeypatch.setattr(main_qt, "MainWindow", lambda _services: calls.append(("window", None, None)))

    main_qt.main()

    assert ("login", True, False) in calls
    assert ("login-exec", None, None) in calls
    assert not any(call[0] == "window" for call in calls)


def test_main_window_persists_and_restores_ui_state_with_store_runtime(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    store, _settings = _store_with_ini(repo_workspace)
    store.save_theme_mode("dark")
    store.save_tab_index(3)
    monkeypatch.setattr("ui.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    first_window = MainWindow(services)
    expected_index = min(3, first_window.tabs.count() - 1)

    assert first_window.theme_combo.currentData() == "dark"
    assert first_window.tabs.currentIndex() == expected_index

    first_window.tabs.setCurrentIndex(1)
    first_window.close()

    assert store.load_tab_index(default_index=0) == 1

    second_window = MainWindow(services)
    assert second_window.theme_combo.currentData() == "dark"
    assert second_window.tabs.currentIndex() == 1
