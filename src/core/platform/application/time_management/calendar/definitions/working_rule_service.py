"""Working rule CRUD service."""

from __future__ import annotations

from datetime import date, time
from typing import Any, Callable

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.time_management.calendar.contracts import (
    CalendarWorkingRuleRepository,
    PlatformCalendarRepository,
)
from src.core.platform.domain.time_management.calendar.enterprise_calendar import CalendarWorkingRule
from src.core.platform.common.exceptions import NotFoundError, ValidationError


class WorkingRuleService:
    def __init__(
        self,
        session: Session,
        calendar_repo: PlatformCalendarRepository,
        rule_repo: CalendarWorkingRuleRepository,
        user_session: Any = None,
        on_calendar_data_changed: Callable[[], None] | None = None,
    ) -> None:
        self._session = session
        self._calendar_repo = calendar_repo
        self._rule_repo = rule_repo
        self._user_session = user_session
        # Invalidates the (process-lifetime) EnterpriseCalendarResolver's rule
        # cache — without this, a saved/deleted rule stays invisible to every
        # resolver-backed read until the app restarts.
        self._on_calendar_data_changed = on_calendar_data_changed

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
        start_time: time | None = None,
        end_time: time | None = None,
        break_start_time: time | None = None,
        break_end_time: time | None = None,
        break_minutes: int = 0,
        hours_override: float | None = None,
        shift_code: str | None = None,
        effective_from: date | None = None,
        effective_to: date | None = None,
        priority: int = 0,
        commit: bool = True,
    ) -> CalendarWorkingRule:
        require_permission(
            self._user_session, "task.manage", operation_label="save working rule"
        )
        candidate = CalendarWorkingRule.create(
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
        self._require_calendar(candidate.calendar_id)

        existing = self._rule_repo.get_for_weekday(candidate.calendar_id, candidate.weekday)
        if existing:
            existing.is_working_day = candidate.is_working_day
            existing.start_time = candidate.start_time
            existing.end_time = candidate.end_time
            existing.break_start_time = candidate.break_start_time
            existing.break_end_time = candidate.break_end_time
            existing.break_minutes = candidate.break_minutes
            existing.hours_override = candidate.hours_override
            existing.shift_code = candidate.shift_code
            existing.effective_from = candidate.effective_from
            existing.effective_to = candidate.effective_to
            existing.priority = candidate.priority
            self._rule_repo.save(existing)
            if commit:
                self._session.commit()
                self._invalidate_resolver_cache()
            else:
                self._session.flush()
            return existing

        self._rule_repo.save(candidate)
        if commit:
            self._session.commit()
            self._invalidate_resolver_cache()
        else:
            self._session.flush()
        return candidate

    def delete_rule(self, rule_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete working rule"
        )
        rule = self._rule_repo.get(rule_id)
        if rule is None:
            raise NotFoundError(f"Working rule '{rule_id}' not found.")
        self._rule_repo.delete(rule_id)
        self._session.commit()
        self._invalidate_resolver_cache()

    def seed_standard_week(
        self,
        calendar_id: str,
        *,
        start_time: time,
        end_time: time,
        break_minutes: int = 60,
        working_days: set[int] | None = None,
    ) -> list[CalendarWorkingRule]:
        """Seed Mon-Fri (or custom set) with a standard schedule. Idempotent.

        All 7 weekday rules are staged and committed together in one
        transaction — a mid-loop failure must not leave a partially-edited
        week, and a partial commit sequence would also fire 7 separate
        `save_rule` commits for what is a single logical "set up this
        calendar's working week" operation."""
        require_permission(
            self._user_session, "task.manage", operation_label="seed working rules"
        )
        self._require_calendar(calendar_id)
        self._validate_time_window(start_time, end_time)
        wd = working_days if working_days is not None else {0, 1, 2, 3, 4}
        rules = []
        try:
            for day in range(7):
                rules.append(
                    self.save_rule(
                        calendar_id,
                        day,
                        is_working_day=day in wd,
                        start_time=start_time if day in wd else None,
                        end_time=end_time if day in wd else None,
                        break_minutes=break_minutes if day in wd else 0,
                        commit=False,
                    )
                )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._invalidate_resolver_cache()
        return rules

    def _invalidate_resolver_cache(self) -> None:
        if self._on_calendar_data_changed is not None:
            self._on_calendar_data_changed()

    def _require_calendar(self, calendar_id: str) -> None:
        if self._calendar_repo.get(calendar_id) is None:
            raise NotFoundError(f"Calendar '{calendar_id}' not found.")

    def _validate_time_window(self, start_time: time, end_time: time) -> None:
        start_min = start_time.hour * 60 + start_time.minute
        end_min = end_time.hour * 60 + end_time.minute
        if end_min <= start_min:
            raise ValidationError("start_time must be before end_time.")


__all__ = ["WorkingRuleService"]
