"""Platform ORM models for runtime execution tracking."""

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

class RuntimeExecutionORM(Base):
    __tablename__ = "runtime_executions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    operation_key: Mapped[str] = mapped_column(String(128), nullable=False)
    module_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", server_default="RUNNING")
    requested_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    requested_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    input_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    output_file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    output_media_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    output_metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}", server_default="{}")
    created_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cancellation_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancellation_requested_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    cancellation_requested_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    retry_of_execution_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
