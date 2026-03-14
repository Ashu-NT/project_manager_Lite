from __future__ import annotations


def test_platform_runtime_application_service_tracks_active_organization_context(services):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]

    assert app_service.current_context_label() == "Default Organization"
    assert app_service.snapshot().context_label == "Default Organization"

    second = organization_service.create_organization(
        organization_code="NORTH",
        display_name="North Division",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )
    app_service.set_active_organization(second.id)

    assert app_service.current_context_label() == "North Division"
    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().organization_code == "NORTH"


def test_platform_runtime_application_service_switches_module_mix_by_organization(services):
    app_service = services["platform_runtime_application_service"]
    default_organization = app_service.get_active_organization()
    assert default_organization is not None

    second = services["organization_service"].create_organization(
        organization_code="SOUTH",
        display_name="South Division",
        timezone_name="Africa/Lagos",
        base_currency="USD",
        is_active=False,
    )

    assert app_service.is_enabled("project_management") is True

    app_service.set_active_organization(second.id)
    app_service.set_module_state("project_management", enabled=False)
    assert app_service.is_enabled("project_management") is False

    app_service.set_active_organization(default_organization.id)
    assert app_service.current_context_label() == "Default Organization"
    assert app_service.is_enabled("project_management") is True


def test_platform_runtime_application_service_exposes_lifecycle_status_changes(services):
    app_service = services["platform_runtime_application_service"]

    trial = app_service.set_module_state("project_management", lifecycle_status="trial")
    assert trial.lifecycle_status == "trial"
    assert trial.runtime_enabled is True

    expired = app_service.set_module_state("project_management", lifecycle_status="expired")
    assert expired.lifecycle_status == "expired"
    assert expired.enabled is False
    assert expired.runtime_enabled is False
    assert app_service.is_enabled("project_management") is False
