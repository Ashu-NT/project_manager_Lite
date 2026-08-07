"""Calendar exception CRUD service."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.time_management.calendar.contracts import (
    CalendarExceptionRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarException,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.application.time_management.calendar.enterprise_calendar_service import _resolve_username


class CalendarExceptionService:
    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        exception_repo: CalendarExceptionRepository,
        user_session: Any = None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._exception_repo = exception_repo
        self._user_session = user_session

    def list_exceptions(
        self,
        calendar_id: str,
        *,
        start: date | None = None,
        end: date | None = None,
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
        scope_type: str | None = None,
        scope_id: str | None = None,
        description: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        hours_override: float | None = None,
        priority: int = 0,
        approval_status: str = "APPROVED",
    ) -> CalendarException:
        require_permission(
            self._user_session, "task.manage", operation_label="add calendar exception"
        )
        self._require_calendar(calendar_id)

        username = _resolve_username(self._user_session)
        exc = CalendarException.create(
            calendar_id=calendar_id,
            exception_date=exception_date,
            exception_type=exception_type,
            name=name,
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
        name: str | None = None,
        description: str | None = None,
        exception_type: str | None = None,
        impact_type: str | None = None,
        start_time: time | None = None,
        end_time: time | None = None,
        hours_override: float | None = None,
        priority: int | None = None,
        approval_status: str | None = None,
        approved_by: str | None = None,
    ) -> CalendarException:
        require_permission(
            self._user_session, "task.manage", operation_label="update calendar exception"
        )
        exc = self._exception_repo.get(exception_id)
        if exc is None:
            raise NotFoundError(f"Exception '{exception_id}' not found.")

        username = _resolve_username(self._user_session)
        updated = replace(
            exc,
            name=exc.name if name is None else name,
            description=exc.description if description is None else description,
            exception_type=exc.exception_type if exception_type is None else exception_type,
            impact_type=exc.impact_type if impact_type is None else impact_type,
            start_time=exc.start_time if start_time is None else start_time,
            end_time=exc.end_time if end_time is None else end_time,
            hours_override=exc.hours_override if hours_override is None else hours_override,
            priority=exc.priority if priority is None else priority,
            approval_status=exc.approval_status if approval_status is None else approval_status,
            approved_by=exc.approved_by if approved_by is None else approved_by,
            updated_by=username,
            updated_at=datetime.now(timezone.utc),
        )
        self._exception_repo.update(updated)
        self._session.commit()
        return updated

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
        self, site_id: str, calendar_id: str, **kwargs: Any
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="site", scope_id=site_id, **kwargs
        )

    def add_department_exception(
        self, department_id: str, calendar_id: str, **kwargs: Any
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="department", scope_id=department_id, **kwargs
        )

    def add_employee_exception(
        self, employee_id: str, calendar_id: str, **kwargs: Any
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="employee", scope_id=employee_id, **kwargs
        )

    def add_resource_exception(
        self, resource_id: str, calendar_id: str, **kwargs: Any
    ) -> CalendarException:
        return self.add_exception(
            calendar_id, scope_type="resource", scope_id=resource_id, **kwargs
        )

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")


__all__ = ["CalendarExceptionService"]
