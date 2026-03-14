from __future__ import annotations

import pytest

from core.platform.common.exceptions import ValidationError
from tests.ui_runtime_helpers import make_settings_store
from ui.platform.shell.main_window import MainWindow


def test_module_catalog_service_bootstraps_persistent_defaults(services):
    catalog = services["module_catalog_service"]

    entitlements = {entitlement.code: entitlement for entitlement in catalog.list_entitlements()}

    assert entitlements["project_management"].licensed is True
    assert entitlements["project_management"].enabled is True
    assert entitlements["maintenance_management"].licensed is False
    assert entitlements["maintenance_management"].enabled is False


def test_module_catalog_service_rejects_licensing_planned_module(services):
    catalog = services["module_catalog_service"]

    with pytest.raises(ValidationError, match="planned"):
        catalog.set_module_state("payroll", licensed=True)


def test_main_window_rebuilds_when_modules_change(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-module-refresh")
    monkeypatch.setattr("ui.platform.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert "Projects" in labels
    assert "Modules" in labels

    services["module_catalog_service"].set_module_state("project_management", enabled=False)
    qapp.processEvents()
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert "Home" in labels
    assert "Modules" in labels
    assert "Projects" not in labels

    services["module_catalog_service"].set_module_state("project_management", enabled=True)
    qapp.processEvents()
    labels = [window.tabs.tabText(i) for i in range(window.tabs.count())]
    assert "Projects" in labels
