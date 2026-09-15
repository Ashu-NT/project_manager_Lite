"""Platform ORM models for organization data."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class OrganizationORM(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("tenant_id", "id", name="uq_organizations_tenant_id"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    organization_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(128), nullable=False, default="UTC", server_default="UTC")
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR", server_default="EUR")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    # Legal identity
    legal_name: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    registration_number: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    tax_id: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    # Registered address
    address_line_1: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    address_line_2: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    postal_code: Mapped[str] = mapped_column(String(32), nullable=False, default="", server_default="")
    city: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    state_region: Mapped[str] = mapped_column(String(128), nullable=False, default="", server_default="")
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, default="", server_default="")
    # Primary contact
    email: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")
    phone: Mapped[str] = mapped_column(String(64), nullable=False, default="", server_default="")
    website: Mapped[str] = mapped_column(String(256), nullable=False, default="", server_default="")


Index("idx_organizations_code", OrganizationORM.organization_code, unique=True)
Index("idx_organizations_enabled", OrganizationORM.is_enabled)
Index("idx_organizations_tenant", OrganizationORM.tenant_id)
