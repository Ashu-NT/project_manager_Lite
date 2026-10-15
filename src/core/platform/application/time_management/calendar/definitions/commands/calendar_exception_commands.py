"""Calendar calendar exception operations."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.time_management.calendar._input import (
    parse_time as _parse_time,
)
from src.core.platform.application.time_management.calendar._input import required_date
from src.core.platform.application.time_management.calendar.commands.platform_calendar_commands import (
    _resolve_username,
)
from src.core.platform.application.time_management.calendar.definitions.dto.commands.calendar_exceptions import (
    ExceptionCreateCommand,
    ExceptionUpdateCommand,
)
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.time_management.calendar.contracts import (
    CalendarExceptionRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    CalendarException,
)


class CalendarExceptionCommandHandler:
    """Transactional writes for calendar exception."""

    def __init__(
        self,
        *,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        exception_repo: CalendarExceptionRepository,
        user_session: Any = None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._exception_repo = exception_repo
        self._user_session = user_session

    def add_exception(self, command: ExceptionCreateCommand) -> CalendarException:
        calendar_id = command.calendar_id
        exception_date = required_date(command.exception_date)
        exception_type = command.exception_type
        name = command.name
        impact_type = command.impact_type
        scope_type = command.scope_type or None
        scope_id = command.scope_id or None
        description = command.description or None
        start_time = _parse_time(command.start_time)
        end_time = _parse_time(command.end_time)
        hours_override = command.hours_override
        priority = command.priority
        approval_status = command.approval_status or "APPROVED"

        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="add calendar exception",
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

    def update_exception(self, command: ExceptionUpdateCommand) -> CalendarException:
        exception_id = command.exception_id
        name = command.name or None
        description = command.description or None
        exception_type = command.exception_type or None
        impact_type = command.impact_type or None
        start_time = command.start_time
        end_time = command.end_time
        hours_override = command.hours_override
        priority = command.priority
        approval_status = command.approval_status or None
        approved_by = command.approved_by or None

        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="update calendar exception",
        )
        exc = self._exception_repo.get(exception_id)
        if exc is None:
            raise NotFoundError(f"Exception '{exception_id}' not found.")

        username = _resolve_username(self._user_session)
        updated = replace(
            exc,
            name=exc.name if name is None else name,
            description=exc.description if description is None else description,
            exception_type=exc.exception_type
            if exception_type is None
            else exception_type,
            impact_type=exc.impact_type if impact_type is None else impact_type,
            start_time=exc.start_time if start_time is None else start_time,
            end_time=exc.end_time if end_time is None else end_time,
            hours_override=exc.hours_override
            if hours_override is None
            else hours_override,
            priority=exc.priority if priority is None else priority,
            approval_status=exc.approval_status
            if approval_status is None
            else approval_status,
            approved_by=exc.approved_by if approved_by is None else approved_by,
            updated_by=username,
            updated_at=datetime.now(UTC),
        )
        self._exception_repo.update(updated)
        self._session.commit()
        return updated

    def delete_exception(self, exception_id: str) -> None:
        require_permission(
            self._user_session,
            "calendar.manage",
            operation_label="delete calendar exception",
        )
        exc = self._exception_repo.get(exception_id)
        if exc is None:
            raise NotFoundError(f"Exception '{exception_id}' not found.")
        self._exception_repo.delete(exception_id)
        self._session.commit()

    # --- Entity-scoped helpers ---

    def add_site_exception(self, command: ExceptionCreateCommand) -> CalendarException:
        return self.add_exception(replace(command, scope_type="site"))

    def add_department_exception(
        self, command: ExceptionCreateCommand
    ) -> CalendarException:
        return self.add_exception(replace(command, scope_type="department"))

    def add_employee_exception(
        self, command: ExceptionCreateCommand
    ) -> CalendarException:
        return self.add_exception(replace(command, scope_type="employee"))

    def add_resource_exception(
        self, command: ExceptionCreateCommand
    ) -> CalendarException:
        return self.add_exception(replace(command, scope_type="resource"))

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")


__all__ = ["CalendarExceptionCommandHandler"]
