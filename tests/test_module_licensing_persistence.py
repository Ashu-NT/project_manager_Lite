from __future__ import annotations

import pytest
from sqlalchemy import text

from core.platform.common.exceptions import BusinessRuleError, ValidationError
from tests.ui_runtime_helpers import make_settings_store
from src.ui.shell.main_window import MainWindow


def test_module_catalog_service_bootstraps_persistent_defaults(services):
    catalog = services["module_catalog_service"]

    entitlements = {entitlement.code: entitlement for entitlement in catalog.list_entitlements()}

    assert entitlements["project_management"].licensed is True
    assert entitlements["project_management"].enabled is True
    assert entitlements["project_management"].lifecycle_status == "active"
    assert entitlements["project_management"].runtime_enabled is True
    assert entitlements["maintenance_management"].licensed is False
    assert entitlements["maintenance_management"].enabled is False
    assert entitlements["maintenance_management"].lifecycle_status == "inactive"
    assert entitlements["maintenance_management"].runtime_enabled is False


def test_module_catalog_service_rejects_licensing_planned_module(services):
    catalog = services["module_catalog_service"]

    with pytest.raises(ValidationError, match="planned"):
        catalog.set_module_state("hr_management", licensed=True)


def test_module_catalog_service_normalizes_legacy_payroll_entitlement_rows_to_hr_management(services, session):
    active_org = services["organization_service"].get_active_organization()
    assert active_org is not None

    session.execute(
        text(
            """
        INSERT INTO organization_module_entitlements (
            organization_id,
            module_code,
            licensed,
            enabled,
            lifecycle_status,
            updated_at
        ) VALUES (
            :organization_id,
            'payroll',
            0,
            0,
            'inactive',
            CURRENT_TIMESTAMP
        )
        """
        ),
        {"organization_id": active_org.id},
    )
    session.commit()

    entitlement = services["module_catalog_service"].set_module_state("hr_management", licensed=False)

    rows = session.execute(
        text("SELECT module_code FROM organization_module_entitlements WHERE organization_id = :organization_id"),
        {"organization_id": active_org.id},
    ).scalars().all()

    assert entitlement.code == "hr_management"
    assert "hr_management" in rows
    assert "payroll" not in rows


def test_main_window_rebuilds_when_modules_change(qapp, services, repo_workspace, monkeypatch):
    store = make_settings_store(repo_workspace, prefix="main-window-module-refresh")
    monkeypatch.setattr("src.ui.shell.main_window.MainWindowSettingsStore", lambda: store)
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


def test_project_management_services_block_direct_calls_when_module_disabled(services):
    catalog = services["module_catalog_service"]
    catalog.set_module_state("project_management", enabled=False)

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled") as project_exc:
        services["project_service"].list_projects()
    assert project_exc.value.code == "MODULE_DISABLED"

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled") as resource_exc:
        services["resource_service"].list_resources()
    assert resource_exc.value.code == "MODULE_DISABLED"

    with pytest.raises(BusinessRuleError, match="Project Management is not enabled") as import_exc:
        services["data_import_service"].get_import_schema("projects")
    assert import_exc.value.code == "MODULE_DISABLED"


def test_module_catalog_service_supports_trial_and_suspended_lifecycle_states(services):
    catalog = services["module_catalog_service"]

    trial = catalog.set_module_state("project_management", lifecycle_status="trial")
    assert trial.lifecycle_status == "trial"
    assert trial.runtime_enabled is True
    assert catalog.is_enabled("project_management") is True

    suspended = catalog.set_module_state("project_management", lifecycle_status="suspended")
    assert suspended.lifecycle_status == "suspended"
    assert suspended.enabled is False
    assert suspended.runtime_enabled is False
    assert catalog.is_enabled("project_management") is False

    with pytest.raises(BusinessRuleError, match="suspended") as suspended_exc:
        services["project_service"].list_projects()
    assert suspended_exc.value.code == "MODULE_DISABLED"
