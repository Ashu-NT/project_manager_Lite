from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.platform.application.master_data.party.queries.party_queries import (
        PartyPage,
    )

from src.core.platform.application.master_data.party.dto.responses.party import (
    PartyDto,
    PartyPageDto,
)
from src.core.platform.domain.master_data.party import Party


def serialize_party_page(page: PartyPage) -> PartyPageDto:
    return PartyPageDto(
        items=tuple(serialize_party(party) for party in page.items),
        total=page.total,
        filtered_total=page.filtered_total,
        page=page.page,
        page_size=page.page_size,
    )


def serialize_party(party: Party) -> PartyDto:
    return PartyDto(
        id=party.id,
        organization_id=party.organization_id,
        party_code=party.party_code,
        party_name=party.party_name,
        party_type=party.party_type,
        roles=party.roles,
        legal_name=party.legal_name,
        contact_name=party.contact_name,
        email=party.email,
        phone=party.phone,
        country=party.country,
        city=party.city,
        address_line_1=party.address_line_1,
        address_line_2=party.address_line_2,
        postal_code=party.postal_code,
        website=party.website,
        registration_number=party.registration_number,
        tax_identifier=party.tax_identifier,
        external_reference=party.external_reference,
        status=party.status.value,
        is_active=party.is_active,
        created_at=party.created_at,
        updated_at=party.updated_at,
        notes=party.notes,
        version=party.version,
    )
