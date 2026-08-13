"""Shift pattern CRUD service."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, time
from typing import Any, Callable

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.contract.time_management.calendar.contracts import ShiftPatternRepository
from src.core.platform.domain.time_management.calendar.enterprise_calendar import (
    ShiftPattern,
    ShiftPatternDay,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError, ValidationError
from src.core.platform.application.tenant.tenancy import TenantContextService


class ShiftPatternService:
    def __init__(
        self,
        session: Session,
        pattern_repo: ShiftPatternRepository,
        organization_repo: Any,
        user_session: Any = None,
        tenant_context_service: TenantContextService | None = None,
        on_calendar_data_changed: Callable[[], None] | None = None,
    ) -> None:
        self._session = session
        self._pattern_repo = pattern_repo
        self._organization_repo = organization_repo
        self._user_session = user_session
        self._tenant_context_service = tenant_context_service
        # Invalidates the (process-lifetime) EnterpriseCalendarResolver's
        # shift-pattern caches — without this, a saved/deleted pattern or day
        # stays invisible to every resolver-backed read until the app restarts.
        self._on_calendar_data_changed = on_calendar_data_changed

    def _active_org_id(self) -> str:
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active organization context is required.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_organization_id(
            operation_label="shift pattern access",
        )

    def list_shift_patterns(
        self, *, active_only: bool | None = None
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
        return self._require_pattern_in_active_organization(pattern_id)

    def create_shift_pattern(
        self,
        *,
        code: str,
        name: str,
        pattern_type: str,
        timezone: str = "UTC",
        description: str | None = None,
        rotation_cycle_days: int | None = None,
        anchor_date: date | None = None,
    ) -> ShiftPattern:
        require_permission(
            self._user_session, "task.manage", operation_label="create shift pattern"
        )
        org_id = self._active_org_id()
        pattern = ShiftPattern.create(
            organization_id=org_id,
            code=code,
            name=name,
            pattern_type=pattern_type,
            timezone=timezone,
            description=description,
            rotation_cycle_days=rotation_cycle_days,
            anchor_date=anchor_date,
        )
        existing = self._pattern_repo.get_by_code(org_id, pattern.code)
        if existing is not None:
            raise ValidationError(f"Shift pattern code '{pattern.code}' already exists.")
        self._pattern_repo.add(pattern)
        self._session.commit()
        self._invalidate_resolver_cache()
        return pattern

    def update_shift_pattern(
        self,
        pattern_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        pattern_type: str | None = None,
        timezone: str | None = None,
        rotation_cycle_days: int | None = None,
        anchor_date: date | None = None,
        is_active: bool | None = None,
    ) -> ShiftPattern:
        require_permission(
            self._user_session, "task.manage", operation_label="update shift pattern"
        )
        pattern = self._require_pattern_in_active_organization(pattern_id)

        updated = replace(
            pattern,
            name=pattern.name if name is None else name,
            description=pattern.description if description is None else description,
            pattern_type=pattern.pattern_type if pattern_type is None else pattern_type,
            timezone=pattern.timezone if timezone is None else timezone,
            rotation_cycle_days=(
                pattern.rotation_cycle_days
                if rotation_cycle_days is None
                else rotation_cycle_days
            ),
            anchor_date=pattern.anchor_date if anchor_date is None else anchor_date,
            is_active=pattern.is_active if is_active is None else is_active,
        )

        self._pattern_repo.update(updated)
        self._session.commit()
        self._invalidate_resolver_cache()
        return updated

    def delete_shift_pattern(self, pattern_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete shift pattern"
        )
        pattern = self._require_pattern_in_active_organization(pattern_id)
        self._pattern_repo.delete(pattern_id)
        self._session.commit()
        self._invalidate_resolver_cache()

    def list_days(self, pattern_id: str) -> list[ShiftPatternDay]:
        require_permission(
            self._user_session, "task.read", operation_label="list shift pattern days"
        )
        self._require_pattern_in_active_organization(pattern_id)
        return self._pattern_repo.list_days(pattern_id)

    def set_day(
        self,
        pattern_id: str,
        day_offset: int,
        *,
        is_working_day: bool = True,
        start_time: time | None = None,
        end_time: time | None = None,
        break_minutes: int = 0,
        hours: float | None = None,
        shift_label: str | None = None,
    ) -> ShiftPatternDay:
        require_permission(
            self._user_session, "task.manage", operation_label="set shift pattern day"
        )
        self._require_pattern_in_active_organization(pattern_id)

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
        self._invalidate_resolver_cache()
        return day

    def delete_day(self, day_id: str) -> None:
        require_permission(
            self._user_session, "task.manage", operation_label="delete shift pattern day"
        )
        self._pattern_repo.delete_day(day_id)
        self._session.commit()
        self._invalidate_resolver_cache()

    def _invalidate_resolver_cache(self) -> None:
        if self._on_calendar_data_changed is not None:
            self._on_calendar_data_changed()

    def _require_pattern_in_active_organization(self, pattern_id: str) -> ShiftPattern:
        org_id = self._active_org_id()
        pattern = self._pattern_repo.get(pattern_id)
        if pattern is None or pattern.organization_id != org_id:
            raise NotFoundError(f"Shift pattern '{pattern_id}' not found.")
        return pattern


__all__ = ["ShiftPatternService"]
