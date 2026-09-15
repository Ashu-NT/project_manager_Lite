"""Desktop API surface for Organization's legal/address/contact fields and
the static country reference list backing the registered-address picker."""

from __future__ import annotations

from src.core.platform.api.desktop.master_data.org.models.organization import (
    OrganizationProvisionCommand,
    OrganizationUpdateCommand,
)
from src.core.platform.api.desktop.platform_runtime.runtime import PlatformRuntimeDesktopApi


def test_list_countries_returns_static_reference_data(services):
    api = PlatformRuntimeDesktopApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    result = api.list_countries()

    assert result.ok is True
    assert result.data is not None
    assert len(result.data) > 100
    codes = {country.code for country in result.data}
    assert "US" in codes
    assert "NL" in codes
    names = {country.code: country.name for country in result.data}
    assert names["US"] == "United States of America"


def test_provision_organization_carries_new_fields_through_the_dto(services):
    api = PlatformRuntimeDesktopApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )

    result = api.provision_organization(
        OrganizationProvisionCommand(
            organization_code="LEGALDESK",
            display_name="Legal Desk Org",
            timezone_name="UTC",
            base_currency="USD",
            is_enabled=False,
            legal_name="Legal Desk Org Holdings",
            registration_number="87654321",
            tax_id="US-TAX-1",
            address_line_1="1 Main St",
            city="Springfield",
            country_code="US",
            email="ops@legaldesk.example",
            phone="+1 555 010 0000",
            website="https://legaldesk.example",
        )
    )

    assert result.ok is True
    assert result.data.legal_name == "Legal Desk Org Holdings"
    assert result.data.registration_number == "87654321"
    assert result.data.tax_id == "US-TAX-1"
    assert result.data.address_line_1 == "1 Main St"
    assert result.data.city == "Springfield"
    assert result.data.country_code == "US"
    assert result.data.email == "ops@legaldesk.example"
    assert result.data.phone == "+1 555 010 0000"
    assert result.data.website == "https://legaldesk.example"


def test_update_organization_carries_new_fields_through_the_dto(services):
    api = PlatformRuntimeDesktopApi(
        platform_runtime_application_service=services["platform_runtime_application_service"]
    )
    created = api.provision_organization(
        OrganizationProvisionCommand(
            organization_code="UPDDESK",
            display_name="Update Desk Org",
            timezone_name="UTC",
            base_currency="USD",
            is_enabled=False,
        )
    ).data

    result = api.update_organization(
        OrganizationUpdateCommand(
            organization_id=created.id,
            legal_name="Update Desk Org Holdings",
            city="Metropolis",
            expected_version=created.version,
        )
    )

    assert result.ok is True
    assert result.data.legal_name == "Update Desk Org Holdings"
    assert result.data.city == "Metropolis"
    # organization_code/display_name pass through unchanged since the update
    # command's other fields stayed None (partial update).
    assert result.data.organization_code == "UPDDESK"
