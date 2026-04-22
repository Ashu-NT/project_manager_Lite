"""Platform ORM models for approval workflow."""

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

class ApprovalRequestORM(Base):
    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    request_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING", server_default="PENDING")
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requested_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    decided_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


Index("idx_approval_status", ApprovalRequestORM.status)
