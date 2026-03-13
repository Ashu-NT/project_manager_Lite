from __future__ import annotations

from core.platform import build_default_module_catalog
from tests.ui_runtime_helpers import make_settings_store
from ui.platform.shell.main_window import MainWindow
from ui.platform.shell import ShellNavigation as PlatformShellNavigation
from ui.platform.shell import ShellNavigation as LegacyShellNavigation


def test_service_graph_exposes_project_management_as_enabled_module(services):
    catalog = services["module_catalog_service"]

    assert catalog.is_enabled("project_management") is True
    assert catalog.is_enabled("maintenance_management") is False
    assert catalog.is_enabled("qhse") is False
    assert catalog.is_enabled("payroll") is False
    assert [module.code for module in catalog.list_enabled_modules()] == ["project_management"]
    assert {module.code for module in catalog.list_planned_modules()} == {
        "maintenance_management",
        "qhse",
        "payroll",
    }


def test_module_catalog_can_enable_future_modules_explicitly():
    catalog = build_default_module_catalog("project_management,payroll")

    assert catalog.is_enabled("project_management") is True
    assert catalog.is_enabled("payroll") is True
    assert catalog.is_enabled("maintenance_management") is False


def test_main_window_runtime_displays_module_summary(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    store = make_settings_store(repo_workspace, prefix="main-window-module-catalog")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    summary = window.shell_navigation.subtitle_label.text()

    assert "Project Management" in summary
    assert "Maintenance Management" in summary
    assert "QHSE" in summary
    assert "Payroll" in summary


def test_legacy_shell_package_reexports_platform_shell():
    assert LegacyShellNavigation is PlatformShellNavigation
