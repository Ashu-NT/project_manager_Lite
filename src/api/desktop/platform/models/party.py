from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.core.platform.party.domain import PartyType


@dataclass(frozen=True)
class PartyDto:
    id: str
    organization_id: str
    party_code: str
    party_name: str
    party_type: PartyType
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
    tax_registration_number: str
    external_reference: str
    is_active: bool
    created_at: datetime | None
    updated_at: datetime | None
    notes: str
    version: int


@dataclass(frozen=True)
class PartyCreateCommand:
    party_code: str
    party_name: str
    party_type: PartyType | str = PartyType.GENERAL
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
    tax_registration_number: str = ""
    external_reference: str = ""
    is_active: bool = True
    notes: str = ""


@dataclass(frozen=True)
class PartyUpdateCommand:
    party_id: str
    party_code: str | None = None
    party_name: str | None = None
    party_type: PartyType | str | None = None
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
    tax_registration_number: str | None = None
    external_reference: str | None = None
    is_active: bool | None = None
    notes: str | None = None
    expected_version: int | None = None
