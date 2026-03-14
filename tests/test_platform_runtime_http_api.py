from __future__ import annotations

from api.http.platform import (
    ModuleStatePatchRequest,
    OrganizationProvisionRequest,
    PlatformRuntimeHttpApi,
)


def test_platform_runtime_http_api_returns_runtime_context_payload(services):
    api = PlatformRuntimeHttpApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    response = api.get_runtime_context()

    assert response.status_code == 200
    assert response.body["context_label"] == "Default Organization"
    assert response.body["active_organization"]["organization_code"] == "DEFAULT"
    assert response.body["enabled_modules"][0]["code"] == "project_management"
    assert any(
        entitlement["module_code"] == "project_management"
        for entitlement in response.body["entitlements"]
    )


def test_platform_runtime_http_api_provisions_organization_with_initial_module_mix(services):
    api = PlatformRuntimeHttpApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    response = api.provision_organization(
        OrganizationProvisionRequest(
            organization_code="OPS",
            display_name="Operations Hub",
            timezone_name="Africa/Lagos",
            base_currency="USD",
            is_active=False,
            initial_module_codes=(),
        )
    )

    assert response.status_code == 201
    assert response.body["data"]["organization_code"] == "OPS"
    assert services["module_catalog_service"].current_context_label() == "Default Organization"
    assert services["module_catalog_service"].is_enabled("project_management") is True

    services["organization_service"].set_active_organization(response.body["data"]["id"])
    assert services["module_catalog_service"].current_context_label() == "Operations Hub"
    assert services["module_catalog_service"].is_enabled("project_management") is False


def test_platform_runtime_http_api_maps_validation_errors(services):
    api = PlatformRuntimeHttpApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    response = api.patch_module_state(
        ModuleStatePatchRequest(
            module_code="payroll",
            licensed=True,
        )
    )

    assert response.status_code == 422
    assert response.body["error"]["code"] == "MODULE_NOT_AVAILABLE"
