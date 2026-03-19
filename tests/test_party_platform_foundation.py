from __future__ import annotations

from core.platform.common.exceptions import ValidationError


def test_party_service_scopes_party_master_data_by_active_organization(services):
    organization_service = services["organization_service"]
    party_service = services["party_service"]

    default_organization = organization_service.get_active_organization()
    created = party_service.create_party(
        party_code="SUP-001",
        party_name="North Supply",
        party_type="SUPPLIER",
        country="Germany",
        city="Berlin",
    )

    assert created.organization_id == default_organization.id
    assert created.party_type.value == "SUPPLIER"
    assert created.country == "Germany"
    assert created.city == "Berlin"
    assert [party.party_name for party in party_service.list_parties()] == ["North Supply"]

    second_organization = organization_service.create_organization(
        organization_code="OPS",
        display_name="Operations Hub",
        timezone_name="Europe/Berlin",
        base_currency="EUR",
        is_active=False,
    )
    organization_service.set_active_organization(second_organization.id)

    assert party_service.get_context_organization().display_name == "Operations Hub"
    assert party_service.list_parties() == []


def test_party_service_rejects_duplicate_codes_inside_one_organization(services):
    party_service = services["party_service"]

    party_service.create_party(party_code="MFG-001", party_name="Plant Works", party_type="MANUFACTURER")

    try:
        party_service.create_party(party_code="MFG-001", party_name="Second Plant", party_type="MANUFACTURER")
    except ValidationError as exc:
        assert exc.code == "PARTY_CODE_EXISTS"
    else:
        raise AssertionError("Expected duplicate party code validation error.")


def test_party_service_updates_party_metadata(services):
    party_service = services["party_service"]
    created = party_service.create_party(party_code="VEN-001", party_name="Field Vendor", party_type="VENDOR")

    updated = party_service.update_party(
        created.id,
        party_name="Field Vendor GmbH",
        party_type="SERVICE_PROVIDER",
        country="Germany",
        city="Hamburg",
        is_active=False,
        expected_version=created.version,
    )

    assert updated.party_name == "Field Vendor GmbH"
    assert updated.party_type.value == "SERVICE_PROVIDER"
    assert updated.country == "Germany"
    assert updated.city == "Hamburg"
    assert updated.is_active is False
