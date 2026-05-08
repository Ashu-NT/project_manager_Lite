from __future__ import annotations

from tests.ui_runtime_helpers import make_settings_store
from src.ui.shell.main_window import MainWindow


def _tab_labels(window: MainWindow) -> list[str]:
    return [window.tabs.tabText(index) for index in range(window.tabs.count())]


def test_module_entitlements_are_scoped_by_active_organization(services):
    organization_service = services["organization_service"]
    module_catalog = services["module_catalog_service"]

    default_organization = organization_service.get_active_organization()
    second_organization = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )

    assert module_catalog.is_enabled("project_management") is True

    organization_service.set_active_organization(second_organization.id)
    assert module_catalog.is_enabled("project_management") is True

    module_catalog.set_module_state("project_management", enabled=False)
    assert module_catalog.is_enabled("project_management") is False

    organization_service.set_active_organization(default_organization.id)
    assert module_catalog.current_context_label() == "Default Organization"
    assert module_catalog.is_enabled("project_management") is True

    organization_service.set_active_organization(second_organization.id)
    assert module_catalog.current_context_label() == "North Division"
    assert module_catalog.is_enabled("project_management") is False


def test_main_window_rebuilds_when_active_organization_changes_module_context(
    qapp,
    services,
    repo_workspace,
    monkeypatch,
):
    organization_service = services["organization_service"]
    module_catalog = services["module_catalog_service"]

    default_organization = organization_service.get_active_organization()
    second_organization = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)
    module_catalog.set_module_state("project_management", enabled=False)
    organization_service.set_active_organization(default_organization.id)

    store = make_settings_store(repo_workspace, prefix="main-window-org-module-context")
    monkeypatch.setattr("src.ui.shell.main_window.MainWindowSettingsStore", lambda: store)
    monkeypatch.setattr(MainWindow, "_run_startup_update_check", lambda self: None)

    window = MainWindow(services)
    assert "Projects" in _tab_labels(window)

    organization_service.set_active_organization(second_organization.id)
    qapp.processEvents()

    assert "Home" in _tab_labels(window)
    assert "Modules" in _tab_labels(window)
    assert "Projects" not in _tab_labels(window)

    organization_service.set_active_organization(default_organization.id)
    qapp.processEvents()

    assert "Projects" in _tab_labels(window)
