"""PM module calendar assignment ORM models."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class ProjectCalendarAssignmentORM(Base):
    __tablename__ = "project_calendar_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


Index("idx_proj_cal_assign_project", ProjectCalendarAssignmentORM.project_id)
Index("idx_proj_cal_assign_cal", ProjectCalendarAssignmentORM.calendar_id)


class ResourceCalendarAssignmentORM(Base):
    __tablename__ = "resource_calendar_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    resource_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False,
    )
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("platform_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    effective_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )


Index("idx_res_cal_assign_resource", ResourceCalendarAssignmentORM.resource_id)
Index("idx_res_cal_assign_cal", ResourceCalendarAssignmentORM.calendar_id)


__all__ = ["ProjectCalendarAssignmentORM", "ResourceCalendarAssignmentORM"]
