"""Register ORM rows."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.modules.project_management.domain.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)
from src.infra.persistence.orm.base import Base


class RegisterEntryORM(Base):
    __tablename__ = "register_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_type: Mapped[RegisterEntryType] = mapped_column(
        SAEnum(RegisterEntryType),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    severity: Mapped[RegisterEntrySeverity] = mapped_column(
        SAEnum(RegisterEntrySeverity),
        nullable=False,
        default=RegisterEntrySeverity.MEDIUM,
        server_default=RegisterEntrySeverity.MEDIUM.value,
    )
    status: Mapped[RegisterEntryStatus] = mapped_column(
        SAEnum(RegisterEntryStatus),
        nullable=False,
        default=RegisterEntryStatus.OPEN,
        server_default=RegisterEntryStatus.OPEN.value,
    )
    owner_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    response_plan: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_register_entries_project", RegisterEntryORM.project_id)
Index("idx_register_entries_type", RegisterEntryORM.entry_type)
Index("idx_register_entries_status", RegisterEntryORM.status)
Index("idx_register_entries_due", RegisterEntryORM.due_date)
