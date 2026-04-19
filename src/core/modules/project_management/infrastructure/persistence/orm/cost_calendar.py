"""Cost and calendar ORM rows."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


class CostItemORM(Base):
    __tablename__ = "cost_items"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    project_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="SET NULL"),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(String, nullable=False)
    cost_type: Mapped[str] = mapped_column(String, nullable=False, default="OVERHEAD")
    currency_code: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    planned_amount: Mapped[float] = mapped_column(Float, nullable=False)
    committed_amount: Mapped[float] = mapped_column(Float, default=0.0)
    actual_amount: Mapped[float] = mapped_column(Float, default=0.0)
    incurred_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")


Index("idx_costs_project", CostItemORM.project_id)
Index("idx_costs_task", CostItemORM.task_id)
Index("idx_costs_type", CostItemORM.cost_type)


class CalendarEventORM(Base):
    __tablename__ = "calendar_events"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    project_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    task_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=True,
    )
    all_day: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(String, default="")


Index("idx_clandar_project", CalendarEventORM.project_id)
Index("idx_calendar_start_end", CalendarEventORM.start_date, CalendarEventORM.end_date)


class WorkingCalendarORM(Base):
    __tablename__ = "working_calendars"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    working_days: Mapped[str] = mapped_column(String, nullable=False, default="0,1,2,3,4")
    hours_per_day: Mapped[float] = mapped_column(Float, default=8.0)


class HolidayORM(Base):
    __tablename__ = "holidays"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    calendar_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("working_calendars.id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String, default="")


Index("idx_holiday_calendar_date", HolidayORM.calendar_id, HolidayORM.date)
