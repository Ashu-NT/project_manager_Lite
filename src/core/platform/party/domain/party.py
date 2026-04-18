from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from core.platform.common.ids import generate_id


class PartyType(str, Enum):
    GENERAL = "GENERAL"
    SUPPLIER = "SUPPLIER"
    MANUFACTURER = "MANUFACTURER"
    VENDOR = "VENDOR"
    CONTRACTOR = "CONTRACTOR"
    SERVICE_PROVIDER = "SERVICE_PROVIDER"


@dataclass
class Party:
    id: str
    organization_id: str
    party_code: str
    party_name: str
    party_type: PartyType = PartyType.GENERAL
    legal_name: str = ""
    contact_name: str = ""
    email: str = ""
    phone: str = ""
    country: str = ""
    city: str = ""
    address_line_1: str = ""
    address_line_2: str = ""
    postal_code: str = ""
    website: str = ""
    tax_registration_number: str = ""
    external_reference: str = ""
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    notes: str = ""
    version: int = 1

    @staticmethod
    def create(
        *,
        organization_id: str,
        party_code: str,
        party_name: str,
        party_type: PartyType = PartyType.GENERAL,
        legal_name: str = "",
        contact_name: str = "",
        email: str = "",
        phone: str = "",
        country: str = "",
        city: str = "",
        address_line_1: str = "",
        address_line_2: str = "",
        postal_code: str = "",
        website: str = "",
        tax_registration_number: str = "",
        external_reference: str = "",
        is_active: bool = True,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        notes: str = "",
    ) -> "Party":
        now = datetime.now(timezone.utc)
        return Party(
            id=generate_id(),
            organization_id=organization_id,
            party_code=party_code,
            party_name=party_name,
            party_type=party_type,
            legal_name=legal_name,
            contact_name=contact_name,
            email=email,
            phone=phone,
            country=country,
            city=city,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            postal_code=postal_code,
            website=website,
            tax_registration_number=tax_registration_number,
            external_reference=external_reference,
            is_active=is_active,
            created_at=created_at or now,
            updated_at=updated_at or now,
            notes=notes,
            version=1,
        )

    @property
    def name(self) -> str:
        return self.party_name

    @name.setter
    def name(self, value: str) -> None:
        self.party_name = value


__all__ = ["Party", "PartyType"]
