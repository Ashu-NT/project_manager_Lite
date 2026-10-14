from __future__ import annotations

from src.core.platform.application.master_data.party.dto import (
    PartyCreateCommand,
    PartyUpdateCommand,
)
from src.core.platform.common.exceptions import ValidationError


def test_party_service_scopes_party_master_data_by_active_organization(services):

    default_organization = services["tenant_context_service"].get_active_organization()
    created = services["party_commands"].create_party(PartyCreateCommand(party_code="SUP-001", party_name="North Supply", roles=["SUPPLIER"], country="Germany", city="Berlin"))

    assert created.organization_id == default_organization.id
    assert created.party_type.value == "ORGANIZATION"
    assert [role.value for role in created.roles] == ["SUPPLIER"]
    assert created.country == "Germany"
    assert created.city == "Berlin"
    assert [party.party_name for party in services["party_query"].list_parties()] == ["North Supply"]

    second_organization = services["organization_commands"].create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
    )
    services["tenant_context_service"].set_active_organization(second_organization.id)

    assert services["party_query"].get_context_organization().display_name == "Operations Hub"
    assert services["party_query"].list_parties() == []


def test_party_service_rejects_duplicate_codes_inside_one_organization(services):

    services["party_commands"].create_party(PartyCreateCommand(party_code="MFG-001", party_name="Plant Works", roles=["MANUFACTURER"]))

    try:
        services["party_commands"].create_party(PartyCreateCommand(party_code="MFG-001", party_name="Second Plant", roles=["MANUFACTURER"]))
    except ValidationError as exc:
        assert exc.code == "PARTY_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate party code validation error.")


def test_party_service_updates_party_metadata(services):
    created = services["party_commands"].create_party(PartyCreateCommand(party_code="VEN-001", party_name="Field Vendor", roles=["VENDOR"]))

    updated = services["party_commands"].update_party(PartyUpdateCommand(party_id=created.id, party_name="Field Vendor GmbH", roles=["SERVICE_PROVIDER"], country="Germany", city="Hamburg", expected_version=created.version))

    assert updated.party_name == "Field Vendor GmbH"
    assert [role.value for role in updated.roles] == ["SERVICE_PROVIDER"]
    assert updated.country == "Germany"
    assert updated.city == "Hamburg"

    deactivated = services["party_commands"].deactivate_party(updated.id)
    assert deactivated.is_active is False

