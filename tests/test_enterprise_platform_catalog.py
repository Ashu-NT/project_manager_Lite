from __future__ import annotations

from pathlib import Path

from application.platform import PlatformRuntimeApplicationService
from core.platform import build_default_module_catalog
from core.platform.modules.runtime import ModuleRuntimeService
from core.platform.modules.service import DEFAULT_ENTERPRISE_MODULES, ModuleCatalogService
from tests.ui_runtime_helpers import make_settings_store
from ui.platform.shell.main_window import MainWindow
from ui.platform.shell.workspaces import build_workspace_definitions
from ui.platform.shell import ShellNavigation as PlatformShellNavigation
from ui.platform.shell import ShellNavigation as LegacyShellNavigation


def test_service_graph_exposes_project_management_as_enabled_module(services):
    catalog = services["module_catalog_service"]
    runtime = services["module_runtime_service"]
    platform_runtime = services["platform_runtime_application_service"]

    assert catalog.is_enabled("project_management") is True
    assert catalog.is_licensed("project_management") is True
    assert catalog.is_enabled("inventory_procurement") is False
    assert catalog.is_enabled("maintenance_management") is False
    assert catalog.is_enabled("qhse") is False
    assert catalog.is_enabled("hr_management") is False
    assert [module.code for module in catalog.list_available_modules()] == ["inventory_procurement"]
    assert [module.code for module in catalog.list_enabled_modules()] == ["project_management"]
    assert [module.code for module in catalog.list_licensed_modules()] == ["project_management"]
    assert {module.code for module in catalog.list_planned_modules()} == {
        "maintenance_management",
        "qhse",
        "hr_management",
    }
    assert "access" in catalog.enabled_capability_codes()
    assert "employees" in catalog.enabled_capability_codes()
    assert "projects" in catalog.enabled_capability_codes()
    assert isinstance(runtime, ModuleRuntimeService)
    assert isinstance(platform_runtime, PlatformRuntimeApplicationService)
    assert runtime.is_enabled("project_management") is True
    assert runtime.get_entitlement("project_management") is not None
    assert "Project Management" in runtime.snapshot().shell_summary
    assert platform_runtime.current_context_label() == "Default Organization"


def test_module_catalog_exposes_platform_base_capabilities():
    catalog = build_default_module_catalog()

    assert [capability.code for capability in catalog.list_platform_capabilities()] == [
        "users",
        "access",
        "audit",
        "approvals",
        "employees",
        "documents",
        "inbox",
        "notifications",
        "settings",
    ]


def test_module_catalog_can_enable_future_modules_explicitly():
    catalog = build_default_module_catalog("project_management,hr_management")

    assert catalog.is_enabled("project_management") is True
    assert catalog.is_licensed("project_management") is True
    assert catalog.is_enabled("hr_management") is True
    assert catalog.is_licensed("hr_management") is True
    assert catalog.is_enabled("maintenance_management") is False


def test_module_catalog_accepts_legacy_payroll_code_as_hr_management_alias():
    catalog = build_default_module_catalog("project_management,payroll")

    assert catalog.is_enabled("hr_management") is True
    assert catalog.is_licensed("hr_management") is True
    assert catalog.is_enabled("payroll") is True
    assert catalog.is_licensed("payroll") is True


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
    assert "Inventory & Procurement" in summary
    assert "Maintenance Management" in summary
    assert "QHSE" in summary
    assert "HR Management" in summary


def test_workspace_definitions_hide_project_management_when_module_disabled(
    qapp,
    services,
    repo_workspace,
):
    services = dict(services)
    services["module_catalog_service"] = ModuleCatalogService(
        modules=DEFAULT_ENTERPRISE_MODULES,
        licensed_codes=(),
        enabled_codes=(),
    )
    settings_store = make_settings_store(repo_workspace, prefix="module-license-platform-only")

    definitions = build_workspace_definitions(
        services=services,
        settings_store=settings_store,
        user_session=services["user_session"],
    )
    labels = [definition.label for definition in definitions]

    assert "Home" in labels
    assert "Users" in labels
    assert "Dashboard" not in labels
    assert "Projects" not in labels
    assert "Tasks" not in labels


def test_legacy_shell_package_reexports_platform_shell():
    assert LegacyShellNavigation is PlatformShellNavigation


def test_shell_workspace_builders_are_split_by_module_packages():
    root = Path(__file__).resolve().parents[1] / "ui" / "platform" / "shell"

    assert (root / "common.py").exists()
    assert (root / "platform" / "__init__.py").exists()
    assert (root / "platform" / "home.py").exists()
    assert (root / "platform" / "workspaces.py").exists()
    assert (root / "project_management" / "__init__.py").exists()
    assert (root / "project_management" / "workspaces.py").exists()
    assert (root / "inventory_procurement" / "__init__.py").exists()
    assert (root / "inventory_procurement" / "workspaces.py").exists()

    coordinator = (root / "workspaces.py").read_text(encoding="utf-8", errors="ignore")
    assert "build_platform_home_workspace_definitions" in coordinator
    assert "build_project_management_workspace_definitions" in coordinator
    assert "build_inventory_procurement_workspace_definitions" in coordinator
    assert "build_platform_administration_workspace_definitions" in coordinator


def test_inventory_procurement_procurement_tabs_are_split_by_subpackages():
    root = Path(__file__).resolve().parents[1] / "ui" / "modules" / "inventory_procurement" / "procurement"

    assert (root / "purchase_orders" / "__init__.py").exists()
    assert (root / "purchase_orders" / "surface.py").exists()
    assert (root / "purchase_orders" / "actions.py").exists()
    assert (root / "purchase_orders" / "views.py").exists()
    assert (root / "purchase_orders" / "tab.py").exists()
    assert (root / "requisitions" / "__init__.py").exists()
    assert (root / "requisitions" / "surface.py").exists()
    assert (root / "requisitions" / "actions.py").exists()
    assert (root / "requisitions" / "views.py").exists()
    assert (root / "requisitions" / "tab.py").exists()


def test_inventory_procurement_removed_dead_top_level_wrappers():
    root = Path(__file__).resolve().parents[1] / "ui" / "modules" / "inventory_procurement"

    removed = [
        "data_exchange_tab.py",
        "document_link_dialogs.py",
        "header_support.py",
        "item_dialogs.py",
        "items_tab.py",
        "movement_dialogs.py",
        "movements_tab.py",
        "procurement_dialogs.py",
        "procurement_support.py",
        "purchase_orders_tab.py",
        "receiving_tab.py",
        "reference_support.py",
        "reports_tab.py",
        "reservation_dialogs.py",
        "reservations_tab.py",
        "requisitions_tab.py",
        "stock_dialogs.py",
        "stock_tab.py",
        "storeroom_dialogs.py",
        "storerooms_tab.py",
    ]

    for relative_path in removed:
        assert not (root / relative_path).exists()


def test_maintenance_management_now_has_core_foundation_packages():
    root = Path(__file__).resolve().parents[1] / "core" / "modules" / "maintenance_management"
    infra_root = Path(__file__).resolve().parents[1] / "infra" / "modules" / "maintenance_management"
    bundle_root = Path(__file__).resolve().parents[1] / "infra" / "platform" / "service_registration"

    assert (root / "domain.py").exists()
    assert (root / "interfaces.py").exists()
    assert (root / "support.py").exists()
    assert (root / "services" / "__init__.py").exists()
    assert (root / "services" / "asset" / "__init__.py").exists()
    assert (root / "services" / "asset" / "service.py").exists()
    assert (root / "services" / "component" / "__init__.py").exists()
    assert (root / "services" / "component" / "service.py").exists()
    assert (root / "services" / "downtime_event" / "__init__.py").exists()
    assert (root / "services" / "downtime_event" / "service.py").exists()
    assert (root / "services" / "failure_code" / "__init__.py").exists()
    assert (root / "services" / "failure_code" / "service.py").exists()
    assert (root / "services" / "integration_source" / "__init__.py").exists()
    assert (root / "services" / "integration_source" / "service.py").exists()
    assert (root / "services" / "location" / "__init__.py").exists()
    assert (root / "services" / "location" / "service.py").exists()
    assert (root / "services" / "sensor_exception" / "__init__.py").exists()
    assert (root / "services" / "sensor_exception" / "service.py").exists()
    assert (root / "services" / "sensor" / "__init__.py").exists()
    assert (root / "services" / "sensor" / "service.py").exists()
    assert (root / "services" / "sensor_reading" / "__init__.py").exists()
    assert (root / "services" / "sensor_reading" / "service.py").exists()
    assert (root / "services" / "sensor_source_mapping" / "__init__.py").exists()
    assert (root / "services" / "sensor_source_mapping" / "service.py").exists()
    assert (root / "services" / "system" / "__init__.py").exists()
    assert (root / "services" / "system" / "service.py").exists()
    assert (root / "services" / "work_request" / "__init__.py").exists()
    assert (root / "services" / "work_request" / "service.py").exists()
    assert (root / "services" / "work_order" / "__init__.py").exists()
    assert (root / "services" / "work_order" / "service.py").exists()
    assert (root / "services" / "work_order_task" / "__init__.py").exists()
    assert (root / "services" / "work_order_task" / "service.py").exists()
    assert (root / "services" / "work_order_task_step" / "__init__.py").exists()
    assert (root / "services" / "work_order_task_step" / "service.py").exists()
    assert (root / "services" / "material_requirement" / "__init__.py").exists()
    assert (root / "services" / "material_requirement" / "service.py").exists()
    assert (infra_root / "db" / "__init__.py").exists()
    assert (infra_root / "db" / "mapper.py").exists()
    assert (infra_root / "db" / "repository.py").exists()
    assert (bundle_root / "maintenance_management_bundle.py").exists()
