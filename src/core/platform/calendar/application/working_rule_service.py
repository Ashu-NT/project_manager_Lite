"""Working rule CRUD service."""

from __future__ import annotations

from datetime import time
from typing import Optional

from sqlalchemy.orm import Session

from src.core.platform.auth.authorization import require_permission
from src.core.platform.calendar.contracts import (
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
)
from src.core.platform.calendar.domain.enterprise_calendar import CalendarWorkingRule
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class WorkingRuleService:
    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        rule_repo: CalendarWorkingRuleRepository,
        user_session=None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._rule_repo = rule_repo
        self._user_session = user_session

    def list_rules(self, calendar_id: str) -> list[CalendarWorkingRule]:
        require_permission(self._user_session, "task.read", operation_label="list working rules")
        self._require_calendar(calendar_id)
        return self._rule_repo.list_for_calendar(calendar_id)

    def save_rule(
        self,
        calendar_id: str,
        weekday: int,
        *,
        is_working_day: bool = True,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        break_start_time: Optional[time] = None,
        break_end_time: Optional[time] = None,
        break_minutes: int = 0,
        hours_override: Optional[float] = None,
        shift_code: Optional[str] = None,
        effective_from=None,
        effective_to=None,
        priority: int = 0,
    ) -> CalendarWorkingRule:
        require_permission(
            self._user_session, "task.manage", operation_label="save working rule"
        )
        self._require_calendar(calendar_id)
        if weekday not in range(7):
            raise ValidationError(f"weekday must be 0-6, got {weekday}.")
        if is_working_day and start_time and end_time:
            self._validate_time_window(start_time, end_time)
        if hours_override is not None and hours_override < 0:
            raise ValidationError("hours_override must be non-negative.")

        existing = self._rule_repo.get_for_weekday(calendar_id, weekday)
        if existing:
            existing.is_working_day = is_working_day
            existing.start_time = start_time
            existing.end_time = end_time
            existing.break_start_time = break_start_time
            existing.break_end_time = break_end_time
            existing.break_minutes = break_minutes
            existing.hours_override = hours_override
            existing.shift_code = shift_code
            existing.effective_from = effective_from
            existing.effective_to = effective_to
            existing.priority = priority
            self._rule_repo.save(existing)
            self._session.commit()
            return existing

        rule = CalendarWorkingRule.create(
            calendar_id=calendar_id,
            weekday=weekday,
            is_working_day=is_working_day,
            start_time=start_time,
            end_time=end_time,
            break_start_time=break_start_time,
            break_end_time=break_end_time,
            break_minutes=break_minutes,
            hours_override=hours_override,
            shift_code=shift_code,
            effective_from=effective_from,
            effective_to=effective_to,
            priority=priority,
        )
        self._rule_repo.save(rule)
        self._session.commit()
        return rule

    def delete_rule(self, rule_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete working rule"
        )
        rule = self._rule_repo.get(rule_id)
        if rule is None:
            raise NotFoundError(f"Working rule '{rule_id}' not found.")
        self._rule_repo.delete(rule_id)
        self._session.commit()

    def seed_standard_week(
        self,
        calendar_id: str,
        *,
        start_time: time,
        end_time: time,
        break_minutes: int = 60,
        working_days: set[int] | None = None,
    ) -> list[CalendarWorkingRule]:
        """Seed Mon-Fri (or custom set) with a standard schedule. Idempotent."""
        require_permission(
            self._user_session, "task.manage", operation_label="seed working rules"
        )
        self._require_calendar(calendar_id)
        self._validate_time_window(start_time, end_time)
        wd = working_days if working_days is not None else {0, 1, 2, 3, 4}
        rules = []
        for day in range(7):
            rules.append(
                self.save_rule(
                    calendar_id,
                    day,
                    is_working_day=day in wd,
                    start_time=start_time if day in wd else None,
                    end_time=end_time if day in wd else None,
                    break_minutes=break_minutes if day in wd else 0,
                )
            )
        return rules

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")

    def _validate_time_window(self, start_time: time, end_time: time) -> None:
        start_min = start_time.hour * 60 + start_time.minute
        end_min = end_time.hour * 60 + end_time.minute
        if end_min <= start_min:
            raise ValidationError("start_time must be before end_time.")


__all__ = ["WorkingRuleService"]
