from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.platform.party.domain import Party
from src.core.platform.party.contracts import PartyRepository
from src.core.platform.infrastructure.persistence.orm.models import PartyORM
from src.infra.persistence.db.optimistic import update_with_version_check
from src.core.platform.infrastructure.persistence.party.mapper import party_from_orm, party_to_orm


class SqlAlchemyPartyRepository(PartyRepository):
    def __init__(self, session: Session):
        self.session = session

    def add(self, party: Party) -> None:
        self.session.add(party_to_orm(party))

    def update(self, party: Party) -> None:
        party.version = update_with_version_check(
            self.session,
            PartyORM,
            party.id,
            getattr(party, "version", 1),
            {
                "party_code": party.party_code,
                "party_name": party.party_name,
                "party_type": party.party_type.value,
                "legal_name": party.legal_name or None,
                "contact_name": party.contact_name or None,
                "email": party.email or None,
                "phone": party.phone or None,
                "country": party.country or None,
                "city": party.city or None,
                "address_line_1": party.address_line_1 or None,
                "address_line_2": party.address_line_2 or None,
                "postal_code": party.postal_code or None,
                "website": party.website or None,
                "tax_registration_number": party.tax_registration_number or None,
                "external_reference": party.external_reference or None,
                "is_active": party.is_active,
                "created_at": party.created_at,
                "updated_at": party.updated_at,
                "notes": party.notes or None,
            },
            not_found_message="Party not found.",
            stale_message="Party was updated by another user.",
        )

    def get(self, party_id: str) -> Party | None:
        obj = self.session.get(PartyORM, party_id)
        return party_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, party_code: str) -> Party | None:
        stmt = select(PartyORM).where(
            PartyORM.organization_id == organization_id,
            PartyORM.party_code == party_code,
        )
        obj = self.session.execute(stmt).scalars().first()
        return party_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Party]:
        stmt = select(PartyORM).where(PartyORM.organization_id == organization_id)
        if active_only is not None:
            stmt = stmt.where(PartyORM.is_active == bool(active_only))
        rows = self.session.execute(stmt.order_by(PartyORM.party_name.asc())).scalars().all()
        return [party_from_orm(row) for row in rows]


__all__ = ["SqlAlchemyPartyRepository"]
