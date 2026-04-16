from __future__ import annotations

from src.api.desktop.platform import (
    ModuleStatePatchCommand,
    OrganizationProvisionCommand,
    PlatformRuntimeDesktopApi,
)
from src.api.desktop.runtime import build_desktop_api_registry


def test_platform_runtime_desktop_api_returns_runtime_context_dto(services):
    api = PlatformRuntimeDesktopApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    result = api.get_runtime_context()

    assert result.ok is True
    assert result.error is None
    assert result.data is not None
    assert result.data.context_label == "Default Organization"
    assert result.data.active_organization is not None
    assert result.data.active_organization.organization_code == "DEFAULT"
    assert result.data.enabled_modules[0].code == "project_management"
    assert any(
        entitlement.module_code == "project_management"
        for entitlement in result.data.entitlements
    )


def test_platform_runtime_desktop_api_provisions_organization_with_initial_module_mix(services):
    api = PlatformRuntimeDesktopApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    result = api.provision_organization(
        OrganizationProvisionCommand(
            organization_code="OPS",
            display_name="Operations Hub",
            timezone_name="Africa/Lagos",
            base_currency="USD",
            is_active=False,
            initial_module_codes=(),
        )
    )

    assert result.ok is True
    assert result.data is not None
    assert result.data.organization_code == "OPS"
    assert services["module_catalog_service"].current_context_label() == "Default Organization"
    assert services["module_catalog_service"].is_enabled("project_management") is True

    services["organization_service"].set_active_organization(result.data.id)
    assert services["module_catalog_service"].current_context_label() == "Operations Hub"
    assert services["module_catalog_service"].is_enabled("project_management") is False


def test_platform_runtime_desktop_api_maps_validation_errors(services):
    api = PlatformRuntimeDesktopApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    result = api.patch_module_state(
        ModuleStatePatchCommand(
            module_code="hr_management",
            licensed=True,
        )
    )

    assert result.ok is False
    assert result.data is None
    assert result.error is not None
    assert result.error.category == "validation"
    assert result.error.code == "MODULE_NOT_AVAILABLE"


def test_build_desktop_api_registry_exposes_platform_runtime_adapter(services):
    registry = build_desktop_api_registry(services)

    result = registry.platform_runtime.list_modules()

    assert result.ok is True
    assert result.data is not None
    assert any(module.code == "project_management" for module in result.data)
