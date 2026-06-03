"""Platform ORM models for organization data."""

from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class OrganizationORM(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    timezone_name: Mapped[str] = mapped_column(String(128), nullable=False, default="UTC", server_default="UTC")
    base_currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR", server_default="EUR")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_organizations_code", OrganizationORM.organization_code, unique=True)
Index("idx_organizations_active", OrganizationORM.is_active)
