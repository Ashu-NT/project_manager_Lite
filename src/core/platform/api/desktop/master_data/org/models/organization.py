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


@dataclass(frozen=True)
class OrganizationCatalogPageDto:
    items: tuple[OrganizationDto, ...] = field(default_factory=tuple)
    total: int = 0
    filtered_total: int = 0
    page: int = 1
    page_size: int = 25


@dataclass(frozen=True)
class OrganizationProvisionCommand:
    organization_code: str
    display_name: str
    timezone_name: str
    base_currency: str
    is_enabled: bool = True
    initial_module_codes: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OrganizationUpdateCommand:
    organization_id: str
    organization_code: str | None = None
    display_name: str | None = None
    timezone_name: str | None = None
    base_currency: str | None = None
    is_enabled: bool | None = None
    expected_version: int | None = None
