"""Transport-neutral party use-case commands (desktop and future HTTP adapters)."""

from __future__ import annotations

from dataclasses import dataclass, field

from src.core.platform.domain.master_data.party import PartyType


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


__all__ = [
    "PartyCreateCommand",
    "PartyUpdateCommand",
]
