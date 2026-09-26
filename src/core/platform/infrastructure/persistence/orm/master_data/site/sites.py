"""Platform site ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class SiteORM(Base):
    __tablename__ = "sites"
    __table_args__ = (
        UniqueConstraint("organization_id", "site_code", name="ux_sites_org_code"),
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
    site_code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    region: Mapped[str | None] = mapped_column(String(128), nullable=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(256), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    currency_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    site_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active", server_default="active")
    default_calendar_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    default_language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_sites_tenant", SiteORM.tenant_id)
Index("idx_sites_organization", SiteORM.organization_id)
Index("idx_sites_status", SiteORM.organization_id, SiteORM.status)
