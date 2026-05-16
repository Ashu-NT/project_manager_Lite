from __future__ import annotations

from pathlib import Path

from src.application.runtime.platform_runtime import PlatformRuntimeApplicationService
from src.application.runtime.entitlement_runtime import ModuleRuntimeService
from src.core.platform.modules import (
    DEFAULT_ENTERPRISE_MODULES,
    build_default_module_catalog,
)
from tests.path_rewrites import REPO_ROOT


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
    assert [module.code for module in catalog.list_available_modules()] == [
        "inventory_procurement",
        "maintenance_management",
    ]
    assert [module.code for module in catalog.list_enabled_modules()] == ["project_management"]
    assert [module.code for module in catalog.list_licensed_modules()] == ["project_management"]
    assert {module.code for module in catalog.list_planned_modules()} == {
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
