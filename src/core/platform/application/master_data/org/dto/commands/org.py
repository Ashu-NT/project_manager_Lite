from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OrganizationProvisionCommand:
    organization_code: str
    display_name: str
    timezone_name: str
    base_currency: str
    # None provisions the catalog's default-enabled modules; an empty tuple provisions none.
    initial_module_codes: tuple[str, ...] | None = None
    legal_name: str = ""
    registration_number: str = ""
    tax_id: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    city: str = ""
    state_region: str = ""
    country_code: str = ""
    email: str = ""
    phone: str = ""
    website: str = ""


@dataclass(frozen=True)
class OrganizationUpdateCommand:
    organization_id: str
    organization_code: str | None = None
    display_name: str | None = None
    timezone_name: str | None = None
    base_currency: str | None = None
    expected_version: int | None = None
    legal_name: str | None = None
    registration_number: str | None = None
    tax_id: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    city: str | None = None
    state_region: str | None = None
    country_code: str | None = None
    email: str | None = None
    phone: str | None = None
    website: str | None = None
