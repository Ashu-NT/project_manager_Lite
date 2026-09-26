"""Organization legal/address/contact fields -- persistence round-trip,
update semantics, and Desktop API/statistics passthrough. Complements
test_organization_legal_address_contact_fields.py (pure domain validation)
and test_organization_pagination.py (pagination mechanics)."""

from __future__ import annotations

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def test_create_with_new_fields_round_trips_through_repository(services):
    organization_service = services["organization_service"]
    code = _unique_code("LEGALFIELDS")
    created = organization_service.create_organization(
        organization_code=code,
        display_name="Legal Fields Org",
        legal_name="Legal Fields Org Holdings B.V.",
        registration_number="12345678",
        tax_id="NL123456789B01",
        address_line_1="Herengracht 1",
        address_line_2="Suite 2",
        postal_code="1015 BA",
        city="Amsterdam",
        state_region="North Holland",
        country_code="NL",
        email="contact@example.com",
        phone="+31 20 555 1234",
        website="https://www.example.com",
    )

    reloaded = organization_service._organization_repo.get(created.id)
    assert reloaded is not None
    assert reloaded.legal_name == "Legal Fields Org Holdings B.V."
    assert reloaded.registration_number == "12345678"
    assert reloaded.tax_id == "NL123456789B01"
    assert reloaded.address_line_1 == "Herengracht 1"
    assert reloaded.address_line_2 == "Suite 2"
    assert reloaded.postal_code == "1015 BA"
    assert reloaded.city == "Amsterdam"
    assert reloaded.state_region == "North Holland"
    assert reloaded.country_code == "NL"
    assert reloaded.email == "contact@example.com"
    assert reloaded.phone == "+31 20 555 1234"
    assert reloaded.website == "https://www.example.com"


def test_create_with_all_new_fields_blank_persists_blank(services):
    organization_service = services["organization_service"]
    code = _unique_code("BLANKFIELDS")
    created = organization_service.create_organization(
        organization_code=code,
        display_name="Blank Fields Org",
    )

    reloaded = organization_service._organization_repo.get(created.id)
    assert reloaded is not None
    assert reloaded.legal_name == ""
    assert reloaded.registration_number == ""
    assert reloaded.tax_id == ""
    assert reloaded.address_line_1 == ""
    assert reloaded.city == ""
    assert reloaded.country_code == ""
    assert reloaded.email == ""
    assert reloaded.phone == ""
    assert reloaded.website == ""


def test_update_changes_only_the_new_fields_provided(services):
    organization_service = services["organization_service"]
    code = _unique_code("UPDATEFIELDS")
    created = organization_service.create_organization(
        organization_code=code,
        display_name="Update Fields Org",
        legal_name="Original Legal Name",
        city="Original City",
    )

    updated = organization_service.update_organization(
        created.id,
        legal_name="New Legal Name",
        expected_version=created.version,
    )

    assert updated.legal_name == "New Legal Name"
    # Untouched fields are preserved, not blanked out by the partial update.
    assert updated.city == "Original City"
    assert updated.organization_code == created.organization_code
    assert updated.display_name == created.display_name


def test_update_can_explicitly_blank_a_field(services):
    organization_service = services["organization_service"]
    code = _unique_code("BLANKUPDATE")
    created = organization_service.create_organization(
        organization_code=code,
        display_name="Blank Update Org",
        phone="+1 555 0000",
    )

    updated = organization_service.update_organization(
        created.id,
        phone="",
        expected_version=created.version,
    )
    assert updated.phone == ""
