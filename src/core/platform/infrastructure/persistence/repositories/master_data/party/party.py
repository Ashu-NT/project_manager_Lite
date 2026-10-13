from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.core.platform.contract.repositories.master_data.party.contracts import (
    PartyRepository,
)
from src.core.platform.domain.master_data.party import Party, PartyLifecycleStatus
from src.core.platform.infrastructure.persistence.mappers.master_data.party.party import (
    party_from_orm,
    party_to_orm,
)
from src.core.platform.infrastructure.persistence.orm.master_data.party.party import (
    PartyORM,
)
from src.core.platform.infrastructure.persistence.repositories._tenant_scope import (
    TenantScopedRepositorySupport,
)
from src.infra.persistence.db.optimistic import update_with_version_check


class SqlAlchemyPartyRepository(TenantScopedRepositorySupport, PartyRepository):
    _repository_label = "PartyRepository"
    session: Session

    def __init__(self, session: Session) -> None:
        self.session = session
        self._tenant_context_service = None

    def add(self, party: Party) -> None:
        ctx = self._context(operation_label="access parties")
        orm = party_to_orm(party)
        orm.tenant_id = ctx.tenant_id
        orm.organization_id = ctx.organization_id
        self.session.add(orm)

    def update(self, party: Party) -> None:
        ctx = self._context(operation_label="access parties")
        party.version = update_with_version_check(
            self.session,
            PartyORM,
            party.id,
            getattr(party, "version", 1),
            {
                "party_code": party.party_code,
                "party_name": party.party_name,
                "party_type": party.party_type.value,
                "roles": ",".join(role.value for role in party.roles),
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
                "registration_number": party.registration_number or None,
                "tax_identifier": party.tax_identifier or None,
                "external_reference": party.external_reference or None,
                "status": party.status,
                "created_at": party.created_at,
                "updated_at": party.updated_at,
                "notes": party.notes or None,
            },
            extra_filters={
                "tenant_id": ctx.tenant_id,
                "organization_id": ctx.organization_id,
            },
            not_found_message="Party not found.",
            stale_message="Party was updated by another user.",
        )

    def get(self, party_id: str) -> Party | None:
        ctx = self._context(operation_label="access parties")
        stmt = select(PartyORM).where(
            PartyORM.id == party_id,
            PartyORM.tenant_id == ctx.tenant_id,
            PartyORM.organization_id == ctx.organization_id,
        )
        obj = self.session.execute(stmt).scalar_one_or_none()
        return party_from_orm(obj) if obj else None

    def get_by_code(self, organization_id: str, party_code: str) -> Party | None:
        ctx = self._context(operation_label="access parties")
        if not self._organization_in_scope(ctx, organization_id):
            return None
        stmt = select(PartyORM).where(
            PartyORM.organization_id == ctx.organization_id,
            PartyORM.party_code == party_code,
            PartyORM.tenant_id == ctx.tenant_id,
        )
        obj = self.session.execute(stmt).scalars().first()
        return party_from_orm(obj) if obj else None

    def list_for_organization(
        self,
        organization_id: str,
        *,
        active_only: bool | None = None,
    ) -> list[Party]:
        ctx = self._context(operation_label="access parties")
        if not self._organization_in_scope(ctx, organization_id):
            return []
        stmt = select(PartyORM).where(
            PartyORM.organization_id == ctx.organization_id,
            PartyORM.tenant_id == ctx.tenant_id,
        )
        if active_only is not None:
            status = PartyLifecycleStatus.ACTIVE if active_only else PartyLifecycleStatus.INACTIVE
            stmt = stmt.where(PartyORM.status == status)
        rows = self.session.execute(stmt.order_by(PartyORM.party_name.asc())).scalars().all()
        return [party_from_orm(row) for row in rows]

    def list_page_for_organization_in_tenant(
        self,
        organization_id: str,
        tenant_id: str,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        active_only: bool | None = None,
        party_type: str | None = None,
        role: str | None = None,
    ) -> tuple[list[Party], int, int]:
        # Deliberately bypasses self._context()/_organization_in_scope() --
        # both organization_id and tenant_id are caller-supplied and
        # trusted, not the session's ambient active organization. Mirrors
        # SqlAlchemyDocumentRepository/SqlAlchemyEmployeeRepository's own
        # established list_page_for_organization_in_tenant pattern.
        base_condition = (
            PartyORM.organization_id == organization_id,
            PartyORM.tenant_id == tenant_id,
        )
        total = self.session.execute(
            select(func.count()).select_from(PartyORM).where(*base_condition)
        ).scalar_one()

        filtered_stmt = select(PartyORM).where(*base_condition)
        filtered_count_stmt = select(func.count()).select_from(PartyORM).where(*base_condition)
        if active_only is not None:
            status = PartyLifecycleStatus.ACTIVE if active_only else PartyLifecycleStatus.INACTIVE
            condition = PartyORM.status == status
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        if party_type:
            condition = PartyORM.party_type == party_type
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        if role:
            # `roles` is a plain comma-separated string column (see the ORM
            # model's own comment) -- a simple LIKE against a
            # comma-delimited substring is sufficient here; no relational
            # join exists (or is needed) for this first pass.
            condition = or_(
                PartyORM.roles == role,
                PartyORM.roles.ilike(f"{role},%"),
                PartyORM.roles.ilike(f"%,{role},%"),
                PartyORM.roles.ilike(f"%,{role}"),
            )
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)
        normalized_search = (search or "").strip()
        if normalized_search:
            pattern = f"%{normalized_search}%"
            condition = or_(
                PartyORM.party_name.ilike(pattern),
                PartyORM.party_code.ilike(pattern),
                PartyORM.legal_name.ilike(pattern),
                PartyORM.country.ilike(pattern),
            )
            filtered_stmt = filtered_stmt.where(condition)
            filtered_count_stmt = filtered_count_stmt.where(condition)

        filtered_total = self.session.execute(filtered_count_stmt).scalar_one()
        offset = max(0, (page - 1) * page_size)
        rows = self.session.execute(
            filtered_stmt.order_by(PartyORM.party_name.asc()).offset(offset).limit(page_size)
        ).scalars().all()
        return [party_from_orm(row) for row in rows], total, filtered_total


__all__ = ["SqlAlchemyPartyRepository"]
