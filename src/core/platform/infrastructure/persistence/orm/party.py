"""Platform ORM models for party master data."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime
from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.core.platform.org.domain import EmploymentType
from src.core.platform.time.domain import TimesheetPeriodStatus
from src.infra.persistence.orm.base import Base

class PartyORM(Base):
    __tablename__ = "parties"
    __table_args__ = (
        UniqueConstraint("organization_id", "party_code", name="ux_parties_org_code"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    party_code: Mapped[str] = mapped_column(String(64), nullable=False)
    party_name: Mapped[str] = mapped_column(String(256), nullable=False)
    party_type: Mapped[str] = mapped_column(String(64), nullable=False)
    legal_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    contact_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    address_line_1: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    address_line_2: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    tax_registration_number: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    external_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_parties_organization", PartyORM.organization_id)
Index("idx_parties_active", PartyORM.organization_id, PartyORM.is_active)
