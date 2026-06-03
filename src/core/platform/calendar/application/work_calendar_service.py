from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_permission
from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol
from src.core.platform.calendar.contracts import WorkingCalendarRepository
from src.core.platform.calendar.domain import Holiday, WorkingCalendar
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.notifications.domain_events import domain_events


class WorkCalendarService:
    """Platform-owned service for working-week rules and holiday exceptions."""

    def __init__(
        self,
        session: Session,
        calendar_repo: WorkingCalendarRepository,
        engine: CalendarProtocol,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._repo = calendar_repo
        self._engine = engine
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _ensure_calendar(self) -> WorkingCalendar:
        calendar = self._repo.get_default()
        if calendar is None:
            calendar = WorkingCalendar.create_default()
            self._repo.upsert(calendar)
            self._session.commit()
        return calendar

    def get_calendar(self) -> WorkingCalendar:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="view working calendar",
        )
        return self._ensure_calendar()

    def set_working_days(
        self,
        working_days: set[int],
        hours_per_day: float | None = None,
    ) -> WorkingCalendar:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="update working calendar",
        )
        calendar = self._ensure_calendar()
        calendar.working_days = working_days
        if hours_per_day is not None:
            if hours_per_day <= 0:
                raise ValidationError("hours_per_day must be positive.")
            calendar.hours_per_day = hours_per_day
        self._repo.upsert(calendar)
        self._session.commit()
        domain_events.calendars_changed.emit(calendar.id)
        return calendar

    def list_holidays(self) -> list[Holiday]:
        require_permission(
            self._user_session,
            "task.read",
            operation_label="list non-working days",
        )
        calendar = self._ensure_calendar()
        return self._repo.list_holidays(calendar.id)

    def add_holiday(self, date_: date, name: str = "") -> Holiday:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="add non-working day",
        )
        calendar = self._ensure_calendar()
        holiday = Holiday.create(calendar_id=calendar.id, date=date_, name=name.strip())
        self._repo.add_holiday(holiday)
        self._session.commit()
        domain_events.calendars_changed.emit(calendar.id)
        return holiday

    def delete_holiday(self, holiday_id: str) -> None:
        require_permission(
            self._user_session,
            "task.manage",
            operation_label="delete non-working day",
        )
        calendar = self._ensure_calendar()
        self._repo.delete_holiday(holiday_id)
        self._session.commit()
        domain_events.calendars_changed.emit(calendar.id)


__all__ = ["WorkCalendarService"]
