"""Platform ORM models for time tracking."""

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

class TimeEntryORM(Base):
    __tablename__ = "time_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    work_allocation_id: Mapped[str] = mapped_column(String, nullable=False)
    assignment_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("task_assignments.id", ondelete="CASCADE"),
        nullable=True,
    )
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    hours: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    owner_type: Mapped[str] = mapped_column(String(64), nullable=False, default="work_allocation", server_default="work_allocation")
    owner_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    scope_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scope_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    employee_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    department_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    site_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("sites.id", ondelete="SET NULL"),
        nullable=True,
    )
    site_name: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    author_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    author_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


Index("idx_time_entries_work_allocation", TimeEntryORM.work_allocation_id)
Index("idx_time_entries_assignment", TimeEntryORM.assignment_id)
Index("idx_time_entries_date", TimeEntryORM.entry_date)
Index("idx_time_entries_owner", TimeEntryORM.owner_type, TimeEntryORM.owner_id)
Index("idx_time_entries_scope", TimeEntryORM.scope_type, TimeEntryORM.scope_id)
Index("idx_time_entries_employee", TimeEntryORM.employee_id)
Index("idx_time_entries_department", TimeEntryORM.department_id)
Index("idx_time_entries_site", TimeEntryORM.site_id)


class TimesheetPeriodORM(Base):
    __tablename__ = "timesheet_periods"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[TimesheetPeriodStatus] = mapped_column(
        SAEnum(TimesheetPeriodStatus),
        nullable=False,
        default=TimesheetPeriodStatus.OPEN,
        server_default=TimesheetPeriodStatus.OPEN.value,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    submitted_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decided_by_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    decided_by_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


Index("idx_timesheet_periods_resource", TimesheetPeriodORM.resource_id)
