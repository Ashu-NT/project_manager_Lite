"""Platform ORM models for audit logging."""

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

class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    actor_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")


Index("idx_audit_logs_occurred_at", AuditLogORM.occurred_at)
