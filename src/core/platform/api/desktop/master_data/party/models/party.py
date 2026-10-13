from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.core.platform.domain.master_data.party import PartyRole, PartyType


@dataclass(frozen=True)
class PartyDto:
    id: str
    organization_id: str
    party_code: str
    party_name: str
    party_type: PartyType
    roles: tuple[PartyRole, ...]
    legal_name: str
    contact_name: str
    email: str
    phone: str
    country: str
    city: str
    address_line_1: str
    address_line_2: str
    postal_code: str
    website: str
    registration_number: str
    tax_identifier: str
    external_reference: str
    # `status` ("active"/"inactive") is the real, sole lifecycle source of
    # truth -- `is_active` is a derived read convenience computed once at
    # serialization time, never persisted separately.
    status: str
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None
    notes: str
    version: int


@dataclass(frozen=True)
class PartyRollupSummaryDto:
    total: int
    active: int


@dataclass(frozen=True)
class PartyPageDto:
    items: tuple[PartyDto, ...]
    total: int
    filtered_total: int
    page: int
    page_size: int


@dataclass(frozen=True)
class PartyCreateCommand:
    party_code: str
    party_name: str
    party_type: PartyType | str = PartyType.ORGANIZATION
    roles: list[str] = field(default_factory=list)
    legal_name: str = ""
    contact_name: str = ""
    email: str | None = None
    phone: str | None = None
    country: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    website: str = ""
    registration_number: str = ""
    tax_identifier: str = ""
    external_reference: str = ""
    notes: str = ""


@dataclass(frozen=True)
class PartyUpdateCommand:
    party_id: str
    party_code: str | None = None
    party_name: str | None = None
    party_type: PartyType | str | None = None
    roles: list[str] | None = None
    legal_name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    country: str | None = None
    city: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    postal_code: str | None = None
    website: str | None = None
    registration_number: str | None = None
    tax_identifier: str | None = None
    external_reference: str | None = None
    notes: str | None = None
    expected_version: int | None = None
