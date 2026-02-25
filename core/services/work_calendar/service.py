# core/services/work_calendar_service.py
from __future__ import annotations
from datetime import date
from typing import List, Set
from sqlalchemy.orm import Session

from core.models import WorkingCalendar, Holiday
from core.interfaces import WorkingCalendarRepository
from core.exceptions import ValidationError
from core.services.auth.authorization import require_permission
from core.services.work_calendar.engine import WorkCalendarEngine


class WorkCalendarService:
    """
    High-level API for configuring the working calendar.
    The engine is read-only; all writes go through this service.
    """

    def __init__(
        self,
        session: Session,
        calendar_repo: WorkingCalendarRepository,
        engine: WorkCalendarEngine,
        user_session=None,
    ):
        self._session: Session = session
        self._repo: WorkingCalendarRepository = calendar_repo
        self._engine: WorkCalendarEngine = engine
        self._user_session = user_session

    def _ensure_calendar(self) -> WorkingCalendar:
        cal = self._repo.get_default()
        if cal is None:
            cal = WorkingCalendar.create_default()  # should have id "default"
            self._repo.upsert(cal)
            self._session.commit()
        return cal

    def get_calendar(self) -> WorkingCalendar:
        return self._ensure_calendar()

    def set_working_days(self, working_days: Set[int], hours_per_day: float | None = None) -> WorkingCalendar:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="update working calendar",
        )
        cal = self._ensure_calendar()
        cal.working_days = working_days
        if hours_per_day is not None:
            if hours_per_day <= 0:
                raise ValidationError("hours_per_day must be positive.")
            cal.hours_per_day = hours_per_day
        self._repo.upsert(cal)
        self._session.commit()
        return cal

    def list_holidays(self) -> List[Holiday]:
        cal = self._ensure_calendar()
        return self._repo.list_holidays(cal.id)

    def add_holiday(self, date_: date, name: str = "") -> Holiday:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="add non-working day",
        )
        cal = self._ensure_calendar()
        holiday = Holiday.create(calendar_id=cal.id, date=date_, name=name.strip())
        self._repo.add_holiday(holiday)
        self._session.commit()
        return holiday

    def delete_holiday(self, holiday_id: str) -> None:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="delete non-working day",
        )
        self._repo.delete_holiday(holiday_id)
        self._session.commit()

