from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infra.persistence.orm.base import Base


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


__all__ = ["HolidayORM", "WorkingCalendarORM"]
