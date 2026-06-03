"""Calendar exception CRUD service."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_permission
from src.core.platform.calendar.contracts import (
    CalendarExceptionRepository,
    PlatformCalendarRepository,
)
from src.core.platform.calendar.domain.enterprise_calendar import (
    CalendarException,
    ExceptionType,
    ImpactType,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError


_VALID_EXCEPTION_TYPES = {t.value for t in ExceptionType}
_VALID_IMPACT_TYPES = {t.value for t in ImpactType}


class CalendarExceptionService:
    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        exception_repo: CalendarExceptionRepository,
        user_session=None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._exception_repo = exception_repo
        self._user_session = user_session

    def list_exceptions(
        self,
        calendar_id: str,
        *,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> list[CalendarException]:
        require_permission(self._user_session, "task.read", operation_label="list exceptions")
        self._require_calendar(calendar_id)
        return self._exception_repo.list_for_calendar(calendar_id, start=start, end=end)

    def add_exception(
        self,
        calendar_id: str,
        *,
        exception_date: date,
        exception_type: str,
        name: str,
        impact_type: str,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        hours_override: Optional[float] = None,
        priority: int = 0,
        approval_status: str = "APPROVED",
    ) -> CalendarException:
        require_permission(
            self._user_session, "task.manage", operation_label="add calendar exception"
        )
        self._require_calendar(calendar_id)
        self._validate_types(exception_type, impact_type)
        if start_time and end_time and end_time <= start_time:
            raise ValidationError("Exception end_time must be after start_time.")
        if hours_override is not None and hours_override < 0:
            raise ValidationError("hours_override must be non-negative.")

        username = (getattr(getattr(self._user_session, "principal", None), "username", None)) if self._user_session else None
        exc = CalendarException.create(
            calendar_id=calendar_id,
            exception_date=exception_date,
            exception_type=exception_type,
            name=name.strip(),
            impact_type=impact_type,
            scope_type=scope_type,
            scope_id=scope_id,
            description=description,
            start_time=start_time,
            end_time=end_time,
            hours_override=hours_override,
            priority=priority,
            approval_status=approval_status,
            created_by=username,
        )
        self._exception_repo.add(exc)
        self._session.commit()
        return exc

    def update_exception(
        self,
        exception_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        exception_type: Optional[str] = None,
        impact_type: Optional[str] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        hours_override: Optional[float] = None,
        priority: Optional[int] = None,
        approval_status: Optional[str] = None,
        approved_by: Optional[str] = None,
    ) -> CalendarException:
        require_permission(
            self._user_session, "task.manage", operation_label="update calendar exception"
        )
        exc = self._exception_repo.get(exception_id)
        if exc is None:
            raise NotFoundError(f"Exception '{exception_id}' not found.")

        if name is not None:
            exc.name = name.strip()
        if description is not None:
            exc.description = description
        if exception_type is not None:
            self._validate_types(exception_type, exc.impact_type)
            exc.exception_type = exception_type
        if impact_type is not None:
            self._validate_types(exc.exception_type, impact_type)
            exc.impact_type = impact_type
        if start_time is not None:
            exc.start_time = start_time
        if end_time is not None:
            exc.end_time = end_time
        if hours_override is not None:
            exc.hours_override = hours_override
        if priority is not None:
            exc.priority = priority
        if approval_status is not None:
            exc.approval_status = approval_status
        if approved_by is not None:
            exc.approved_by = approved_by

        username = (getattr(getattr(self._user_session, "principal", None), "username", None)) if self._user_session else None
        exc.updated_by = username
        exc.updated_at = datetime.utcnow()
        self._exception_repo.update(exc)
        self._session.commit()
        return exc

    def delete_exception(self, exception_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete calendar exception"
        )
        exc = self._exception_repo.get(exception_id)
        if exc is None:
            raise NotFoundError(f"Exception '{exception_id}' not found.")
        self._exception_repo.delete(exception_id)
        self._session.commit()

    # --- Entity-scoped helpers ---

    def add_site_exception(
        self, site_id: str, calendar_id: str, **kwargs
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="site", scope_id=site_id, **kwargs
        )

    def add_department_exception(
        self, department_id: str, calendar_id: str, **kwargs
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="department", scope_id=department_id, **kwargs
        )

    def add_employee_exception(
        self, employee_id: str, calendar_id: str, **kwargs
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="employee", scope_id=employee_id, **kwargs
        )

    def add_resource_exception(
        self, resource_id: str, calendar_id: str, **kwargs
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="resource", scope_id=resource_id, **kwargs
        )

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")

    def _validate_types(self, exception_type: str, impact_type: str) -> None:
        if exception_type not in _VALID_EXCEPTION_TYPES:
            raise ValidationError(
                f"Invalid exception_type '{exception_type}'. "
                f"Valid: {sorted(_VALID_EXCEPTION_TYPES)}"
            )
        if impact_type not in _VALID_IMPACT_TYPES:
            raise ValidationError(
                f"Invalid impact_type '{impact_type}'. "
                f"Valid: {sorted(_VALID_IMPACT_TYPES)}"
            )


__all__ = ["CalendarExceptionService"]
