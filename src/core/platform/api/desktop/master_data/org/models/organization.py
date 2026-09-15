from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OrganizationDto:
    id: str
    organization_code: str
    display_name: str
    timezone_name: str
    base_currency: str
    is_enabled: bool
    version: int
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
class OrganizationCatalogPageDto:
    items: tuple[OrganizationDto, ...] = field(default_factory=tuple)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True)
class OrganizationStatisticsDto:
    site_count: int = 0
    department_count: int = 0
    employee_count: int = 0
    document_count: int = 0


@dataclass(frozen=True)
class OrganizationProvisionCommand:
    organization_code: str
    display_name: str
    timezone_name: str
    base_currency: str
    is_enabled: bool = True
    initial_module_codes: tuple[str, ...] = field(default_factory=tuple)
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
    is_enabled: bool | None = None
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
