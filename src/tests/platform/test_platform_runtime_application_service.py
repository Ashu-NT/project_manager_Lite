from __future__ import annotations

import pytest

from src.core.platform.auth.domain.session import UserSessionPrincipal
from src.core.platform.common.exceptions import BusinessRuleError


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
    organization_service.set_active_organization(second.id)
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

    services["organization_service"].set_active_organization(second.id)
    app_service.set_active_organization(second.id)
    app_service.set_module_state("project_management", enabled=False)
    assert app_service.is_enabled("project_management") is False

    services["organization_service"].set_active_organization(default_organization.id)
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


def test_platform_runtime_application_service_provisions_organization_with_initial_module_mix(services):
    app_service = services["platform_runtime_application_service"]

    default_organization = app_service.get_active_organization()
    assert default_organization is not None
    assert app_service.is_enabled("project_management") is True

    provisioned = app_service.provision_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="Africa/Lagos",
        base_currency="USD",
        is_active=False,
        initial_module_codes=[],
    )

    assert provisioned.organization_code == "OPS"
    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().organization_code == "DEFAULT"
    assert app_service.is_enabled("project_management") is True

    services["organization_service"].set_active_organization(provisioned.id)
    app_service.set_active_organization(provisioned.id)
    assert app_service.current_context_label() == "Operations Hub"
    assert app_service.is_enabled("project_management") is False


def test_platform_runtime_application_service_requires_settings_manage_to_switch_context(
    services,
):
    app_service = services["platform_runtime_application_service"]
    organization_service = services["organization_service"]
    user_session = services["user_session"]

    default_organization = app_service.get_active_organization()
    assert default_organization is not None
    second = organization_service.create_organization(
        organization_code="WEST",
        display_name="West Division",
        timezone_name="America/Chicago",
        base_currency="USD",
        is_active=False,
    )

    user_session.set_principal(
        UserSessionPrincipal(
            user_id="user-1",
            username="planner",
            display_name="Planner",
            role_names=frozenset(),
            permissions=frozenset({"organization.access"}),
            scoped_access={
                "organization": {
                    default_organization.id: frozenset({"organization.access"}),
                    second.id: frozenset({"organization.access"}),
                }
            },
            active_organization_id=default_organization.id,
        )
    )
    user_session.set_active_organization_id(default_organization.id)

    with pytest.raises(BusinessRuleError, match="settings.manage"):
        app_service.set_active_organization(second.id)

    assert app_service.get_active_organization() is not None
    assert app_service.get_active_organization().id == default_organization.id

