from __future__ import annotations

from core.platform.party.domain import Party, PartyType
from src.infra.persistence.orm.platform.models import PartyORM


def party_to_orm(party: Party) -> PartyORM:
    return PartyORM(
        id=party.id,
        organization_id=party.organization_id,
        party_code=party.party_code,
        party_name=party.party_name,
        party_type=party.party_type.value,
        legal_name=party.legal_name or None,
        contact_name=party.contact_name or None,
        email=party.email or None,
        phone=party.phone or None,
        country=party.country or None,
        city=party.city or None,
        address_line_1=party.address_line_1 or None,
        address_line_2=party.address_line_2 or None,
        postal_code=party.postal_code or None,
        website=party.website or None,
        tax_registration_number=party.tax_registration_number or None,
        external_reference=party.external_reference or None,
        is_active=party.is_active,
        created_at=party.created_at,
        updated_at=party.updated_at,
        notes=party.notes or None,
        version=getattr(party, "version", 1),
    )


def party_from_orm(obj: PartyORM) -> Party:
    return Party(
        id=obj.id,
        organization_id=obj.organization_id,
        party_code=obj.party_code,
        party_name=obj.party_name,
        party_type=PartyType(obj.party_type),
        legal_name=obj.legal_name or "",
        contact_name=obj.contact_name or "",
        email=obj.email or "",
        phone=obj.phone or "",
        country=obj.country or "",
        city=obj.city or "",
        address_line_1=obj.address_line_1 or "",
        address_line_2=obj.address_line_2 or "",
        postal_code=obj.postal_code or "",
        website=obj.website or "",
        tax_registration_number=obj.tax_registration_number or "",
        external_reference=obj.external_reference or "",
        is_active=obj.is_active,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        notes=obj.notes or "",
        version=getattr(obj, "version", 1),
    )


__all__ = ["party_from_orm", "party_to_orm"]
