"""Platform ORM models for party master data."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.platform.domain.master_data.party import PartyLifecycleStatus
from src.infra.persistence.orm.base import Base


class PartyORM(Base):
    __tablename__ = "parties"
    __table_args__ = (
        UniqueConstraint("organization_id", "party_code", name="ux_parties_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_code: Mapped[str] = mapped_column(String(64), nullable=False)
    party_name: Mapped[str] = mapped_column(String(256), nullable=False)
    # Identity axis (ORGANIZATION/INDIVIDUAL) -- what the Party IS, never
    # conflated with the business role(s) it plays (see `roles` below).
    party_type: Mapped[str] = mapped_column(String(32), nullable=False, default="ORGANIZATION", server_default="ORGANIZATION")
    # Additive business role tags (SUPPLIER/CUSTOMER/CONTRACTOR/...),
    # stored as a plain comma-separated string -- a Party may hold several
    # at once, and no current/near-term consumer needs a queryable
    # relational join on individual roles, so a child table would be
    # premature. Domain's own coerce_party_roles() already round-trips
    # this exact comma-separated shape (also the natural CSV import/export
    # cell format for a multi-value field).
    roles: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    legal_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    email: Mapped[str | None] = mapped_column(String(256), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(256), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Split from the old single `tax_registration_number` -- a company
    # registration number and a VAT/tax identifier are two different
    # real-world identifiers that don't share a format.
    registration_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tax_identifier: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Sole lifecycle source of truth -- never a second persisted `is_active`
    # boolean alongside it (see Party.is_active, a computed domain
    # property, not a column). values_callable is required: without it
    # SQLAlchemy stores/reads by enum member NAME ("ACTIVE") instead of
    # VALUE ("active"), which silently mismatches a migration-backfilled
    # plain-VARCHAR column (this exact mistake was made and fixed on
    # Employee's own status column earlier -- never repeat it).
    status: Mapped[PartyLifecycleStatus] = mapped_column(
        SAEnum(PartyLifecycleStatus, values_callable=lambda enum_cls: [m.value for m in enum_cls]),
        nullable=False,
        default=PartyLifecycleStatus.ACTIVE,
        server_default=PartyLifecycleStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_parties_tenant", PartyORM.tenant_id)
Index("idx_parties_organization", PartyORM.organization_id)
Index("idx_parties_status", PartyORM.organization_id, PartyORM.status)
