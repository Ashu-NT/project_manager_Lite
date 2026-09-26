"""Organization's legal identity / registered address / contact fields --
domain-level construction, normalization, and blank-value defaults. These
fields are optional profile data (never required for a valid Organization),
distinct from operational site/facility data which stays on Site."""

from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.master_data.org import Organization


def test_create_with_all_new_fields_blank_is_valid() -> None:
    organization = Organization.create(
        organization_code="ACME",
        display_name="Acme Corp",
        tenant_id="tenant-a",
    )
    assert organization.legal_name == ""
    assert organization.registration_number == ""
    assert organization.tax_id == ""
    assert organization.address_line_1 == ""
    assert organization.address_line_2 == ""
    assert organization.postal_code == ""
    assert organization.city == ""
    assert organization.state_region == ""
    assert organization.country_code == ""
    assert organization.email == ""
    assert organization.phone == ""
    assert organization.website == ""


def test_create_with_all_new_fields_populated() -> None:
    organization = Organization.create(
        organization_code="ACME",
        display_name="Acme Corp",
        tenant_id="tenant-a",
        legal_name="  Acme Corp Holdings B.V.  ",
        registration_number=" 12345678 ",
        tax_id=" NL123456789B01 ",
        address_line_1="  Herengracht 1  ",
        address_line_2="  Suite 2  ",
        postal_code=" 1015 BA ",
        city="  Amsterdam  ",
        state_region="  North Holland  ",
        country_code=" nl ",
        email="  Contact@Acme.Example  ",
        phone="  +31 20 555 1234  ",
        website="  https://www.acme.example  ",
    )
    assert organization.legal_name == "Acme Corp Holdings B.V."
    assert organization.registration_number == "12345678"
    assert organization.tax_id == "NL123456789B01"
    assert organization.address_line_1 == "Herengracht 1"
    assert organization.address_line_2 == "Suite 2"
    assert organization.postal_code == "1015 BA"
    assert organization.city == "Amsterdam"
    assert organization.state_region == "North Holland"
    assert organization.country_code == "NL"
    assert organization.email == "contact@acme.example"
    assert organization.phone == "+31 20 555 1234"
    assert organization.website == "https://www.acme.example"


def test_registration_number_and_tax_id_are_not_rewritten_beyond_trimming() -> None:
    # Legal identifiers must not be silently reformatted -- only whitespace
    # is trimmed, case and internal formatting are preserved verbatim.
    organization = Organization.create(
        organization_code="ACME",
        display_name="Acme Corp",
        tenant_id="tenant-a",
        registration_number="  Kvk-12345678  ",
        tax_id="  nl123456789b01  ",
    )
    assert organization.registration_number == "Kvk-12345678"
    assert organization.tax_id == "nl123456789b01"


def test_blank_email_is_valid() -> None:
    organization = Organization.create(
        organization_code="ACME", display_name="Acme Corp", tenant_id="tenant-a", email="   "
    )
    assert organization.email == ""


def test_invalid_email_format_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Organization.create(
            organization_code="ACME",
            display_name="Acme Corp",
            tenant_id="tenant-a",
            email="not-an-email",
        )
    assert exc_info.value.code == "ORGANIZATION_EMAIL_INVALID"


def test_phone_has_no_format_restriction() -> None:
    organization = Organization.create(
        organization_code="ACME",
        display_name="Acme Corp",
        tenant_id="tenant-a",
        phone="+1 (555) 000-1234 ext. 5",
    )
    assert organization.phone == "+1 (555) 000-1234 ext. 5"


def test_country_code_is_trimmed_and_uppercased() -> None:
    organization = Organization.create(
        organization_code="ACME", display_name="Acme Corp", tenant_id="tenant-a", country_code="us"
    )
    assert organization.country_code == "US"
