"""Shift pattern CRUD service."""

from __future__ import annotations

from datetime import time
from typing import Optional

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_permission
from src.core.platform.calendar.contracts import ShiftPatternRepository
from src.core.platform.calendar.domain.enterprise_calendar import (
    PatternType,
    ShiftPattern,
    ShiftPatternDay,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError


_VALID_PATTERN_TYPES = {t.value for t in PatternType}


class ShiftPatternService:
    def __init__(
        self,
        session: Session,
        pattern_repo: ShiftPatternRepository,
        organization_repo,
        user_session=None,
    ) -> None:
        self._session = session
        self._pattern_repo = pattern_repo
        self._organization_repo = organization_repo
        self._user_session = user_session

    def _active_org_id(self) -> str:
        org = self._organization_repo.get_active()
        if org is None:
            raise BusinessRuleError("No active organization found.")
        return org.id

    def list_shift_patterns(
        self, *, active_only: Optional[bool] = None
    ) -> list[ShiftPattern]:
        require_permission(
            self._user_session, "task.read", operation_label="list shift patterns"
        )
        org_id = self._active_org_id()
        return self._pattern_repo.list_for_organization(org_id, active_only=active_only)

    def get_shift_pattern(self, pattern_id: str) -> ShiftPattern:
        require_permission(
            self._user_session, "task.read", operation_label="get shift pattern"
        )
        pattern = self._pattern_repo.get(pattern_id)
        if pattern is None:
            raise NotFoundError(f"Shift pattern '{pattern_id}' not found.")
        return pattern

    def create_shift_pattern(
        self,
        *,
        code: str,
        name: str,
        pattern_type: str,
        timezone: str = "UTC",
        description: Optional[str] = None,
        rotation_cycle_days: Optional[int] = None,
    ) -> ShiftPattern:
        require_permission(
            self._user_session, "task.manage", operation_label="create shift pattern"
        )
        if pattern_type not in _VALID_PATTERN_TYPES:
            raise ValidationError(
                f"Invalid pattern_type '{pattern_type}'. Valid: {sorted(_VALID_PATTERN_TYPES)}"
            )
        org_id = self._active_org_id()
        existing = self._pattern_repo.get_by_code(org_id, code.strip())
        if existing is not None:
            raise ValidationError(f"Shift pattern code '{code}' already exists.")

        pattern = ShiftPattern.create(
            organization_id=org_id,
            code=code.strip(),
            name=name.strip(),
            pattern_type=pattern_type,
            timezone=timezone or "UTC",
            description=description,
            rotation_cycle_days=rotation_cycle_days,
        )
        self._pattern_repo.add(pattern)
        self._session.commit()
        return pattern

    def update_shift_pattern(
        self,
        pattern_id: str,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        pattern_type: Optional[str] = None,
        timezone: Optional[str] = None,
        rotation_cycle_days: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> ShiftPattern:
        require_permission(
            self._user_session, "task.manage", operation_label="update shift pattern"
        )
        pattern = self._pattern_repo.get(pattern_id)
        if pattern is None:
            raise NotFoundError(f"Shift pattern '{pattern_id}' not found.")

        if name is not None:
            pattern.name = name.strip()
        if description is not None:
            pattern.description = description
        if pattern_type is not None:
            if pattern_type not in _VALID_PATTERN_TYPES:
                raise ValidationError(f"Invalid pattern_type '{pattern_type}'.")
            pattern.pattern_type = pattern_type
        if timezone is not None:
            pattern.timezone = timezone
        if rotation_cycle_days is not None:
            pattern.rotation_cycle_days = rotation_cycle_days
        if is_active is not None:
            pattern.is_active = is_active

        self._pattern_repo.update(pattern)
        self._session.commit()
        return pattern

    def delete_shift_pattern(self, pattern_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete shift pattern"
        )
        pattern = self._pattern_repo.get(pattern_id)
        if pattern is None:
            raise NotFoundError(f"Shift pattern '{pattern_id}' not found.")
        self._pattern_repo.delete(pattern_id)
        self._session.commit()

    def list_days(self, pattern_id: str) -> list[ShiftPatternDay]:
        require_permission(
            self._user_session, "task.read", operation_label="list shift pattern days"
        )
        if self._pattern_repo.get(pattern_id) is None:
            raise NotFoundError(f"Shift pattern '{pattern_id}' not found.")
        return self._pattern_repo.list_days(pattern_id)

    def set_day(
        self,
        pattern_id: str,
        day_offset: int,
        *,
        is_working_day: bool = True,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        break_minutes: int = 0,
        hours: Optional[float] = None,
        shift_label: Optional[str] = None,
    ) -> ShiftPatternDay:
        require_permission(
            self._user_session, "task.manage", operation_label="set shift pattern day"
        )
        if self._pattern_repo.get(pattern_id) is None:
            raise NotFoundError(f"Shift pattern '{pattern_id}' not found.")
        if day_offset < 0:
            raise ValidationError("day_offset must be >= 0.")
        if is_working_day and start_time and end_time:
            s = start_time.hour * 60 + start_time.minute
            e = end_time.hour * 60 + end_time.minute
            if e <= s:
                raise ValidationError("start_time must be before end_time.")

        day = ShiftPatternDay.create(
            shift_pattern_id=pattern_id,
            day_offset=day_offset,
            is_working_day=is_working_day,
            start_time=start_time,
            end_time=end_time,
            break_minutes=break_minutes,
            hours=hours,
            shift_label=shift_label,
        )
        self._pattern_repo.save_day(day)
        self._session.commit()
        return day

    def delete_day(self, day_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete shift pattern day"
        )
        self._pattern_repo.delete_day(day_id)
        self._session.commit()


__all__ = ["ShiftPatternService"]
