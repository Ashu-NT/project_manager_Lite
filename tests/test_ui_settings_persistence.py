from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings

import main_qt
import src.ui_qml.shell.app as shell_app
from src.infra.platform.app_settings import AppSettingsStore


def _store_with_ini(root: Path):
    ini_path = root / "ui_settings.ini"
    settings = QSettings(str(ini_path), QSettings.IniFormat)
    settings.clear()
    settings.sync()
    return AppSettingsStore(settings), settings


def test_app_settings_store_round_trip(repo_workspace):
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


def test_app_settings_store_normalizes_invalid_values(repo_workspace):
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


def test_main_qt_loads_theme_from_settings_before_qml_shell(repo_workspace, services, monkeypatch):
    store, _settings = _store_with_ini(repo_workspace)
    store.save_theme_mode("dark")
    store.save_governance_mode("required")
    runtime_services = dict(services)
    runtime_services["desktop_api_registry"] = object()

    calls: list[tuple[str, object, object]] = []

    class _FakeApp:
        def __init__(self, _argv):
            calls.append(("app", None, None))

        def setWindowIcon(self, _icon):
            return None

        def setFont(self, _font):
            return None

        def exec(self):
            calls.append(("exec", None, None))
            return 0

    monkeypatch.setenv("PM_SKIP_LOGIN", "1")
    monkeypatch.setattr(shell_app, "QGuiApplication", _FakeApp)
    monkeypatch.setattr(shell_app, "QIcon", lambda path: path)
    monkeypatch.setattr(shell_app, "QFont", lambda family, size: (family, size))
    monkeypatch.setattr(shell_app, "resource_path", lambda rel_path: rel_path)
    monkeypatch.setattr(shell_app, "setup_logging", lambda: None)
    monkeypatch.setattr(shell_app, "build_services", lambda: runtime_services)
    monkeypatch.setattr(shell_app, "AppSettingsStore", lambda: store)
    monkeypatch.setattr(shell_app, "_prompt_for_login_qml", lambda **_kwargs: True)
    monkeypatch.setattr(shell_app, "create_qml_engine", lambda: object())
    monkeypatch.setattr(
        shell_app,
        "load_qml",
        lambda _engine, _path, *, initial_properties=None: calls.append(
            (
                "load",
                initial_properties["shellModel"].themeMode if initial_properties else None,
                (
                    os.getenv("PM_THEME"),
                    os.getenv("PM_GOVERNANCE_MODE"),
                ),
            )
        ),
    )

    main_qt.main()

    load_index = next(i for i, call in enumerate(calls) if call[0] == "load")
    assert load_index > 0
    assert calls[load_index] == ("load", "dark", ("dark", "required"))


def test_main_qt_skip_login_does_not_bypass_unauthenticated_services(
    repo_workspace,
    anonymous_services,
    monkeypatch,
):
    store, _settings = _store_with_ini(repo_workspace)
    calls: list[tuple[str, object, object]] = []
    runtime_services = dict(anonymous_services)
    runtime_services["desktop_api_registry"] = object()

    class _FakeApp:
        def __init__(self, _argv):
            calls.append(("app", None, None))

        def setWindowIcon(self, _icon):
            return None

        def setFont(self, _font):
            return None

        def exec(self):
            calls.append(("exec", None, None))
            return 0

    def _fake_prompt_for_login_qml(*, auth_service, user_session):
        calls.append(("login", auth_service is anonymous_services["auth_service"], user_session.is_authenticated()))
        return False

    monkeypatch.setenv("PM_SKIP_LOGIN", "1")
    monkeypatch.setattr(shell_app, "QGuiApplication", _FakeApp)
    monkeypatch.setattr(shell_app, "QIcon", lambda path: path)
    monkeypatch.setattr(shell_app, "QFont", lambda family, size: (family, size))
    monkeypatch.setattr(shell_app, "resource_path", lambda rel_path: rel_path)
    monkeypatch.setattr(shell_app, "setup_logging", lambda: None)
    monkeypatch.setattr(shell_app, "build_services", lambda: runtime_services)
    monkeypatch.setattr(shell_app, "AppSettingsStore", lambda: store)
    monkeypatch.setattr(shell_app, "_prompt_for_login_qml", _fake_prompt_for_login_qml)
    monkeypatch.setattr(
        shell_app,
        "load_qml",
        lambda *_args, **_kwargs: calls.append(("load", None, None)),
    )

    main_qt.main()

    assert ("login", True, False) in calls
    assert not any(call[0] == "load" for call in calls)
