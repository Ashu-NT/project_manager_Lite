from __future__ import annotations

from datetime import date, datetime, timezone

from core.exceptions import ValidationError
from core.models import TimesheetPeriod, TimesheetPeriodStatus
from core.services.audit.helpers import record_audit
from core.services.auth.authorization import require_permission


class TimesheetPeriodsMixin:
    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        require_permission(self._user_session, "task.manage", operation_label="submit timesheet period")
        entries = self.list_time_entries_for_resource_period(resource_id, period_start=period_start)
        if not entries:
            raise ValidationError("Cannot submit an empty timesheet period.")
        period = self._get_or_create_timesheet_period(resource_id=resource_id, period_start=period_start)
        if period.status in {TimesheetPeriodStatus.SUBMITTED, TimesheetPeriodStatus.APPROVED, TimesheetPeriodStatus.LOCKED}:
            raise ValidationError(
                f"Timesheet period {period.period_start.isoformat()} is already {period.status.value.lower()}."
            )
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.SUBMITTED
        period.submitted_at = datetime.now(timezone.utc)
        period.submitted_by_user_id = getattr(principal, "user_id", None)
        period.submitted_by_username = getattr(principal, "username", None)
        period.decided_at = None
        period.decided_by_user_id = None
        period.decided_by_username = None
        period.decision_note = (note or "").strip() or None
        period.locked_at = None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.submit",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(
                period=period,
                entry_count=len(entries),
                total_hours=self._sum_entry_hours(entries),
            ),
        )
        return period

    def approve_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        require_permission(self._user_session, "approval.decide", operation_label="approve timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be approved.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = (note or "").strip() or None
        period.locked_at = period.decided_at
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.approve",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(
                period=period,
                entry_count=len(entries),
                total_hours=self._sum_entry_hours(entries),
            ),
        )
        return period

    def reject_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        require_permission(self._user_session, "approval.decide", operation_label="reject timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be rejected.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = (note or "").strip() or None
        period.locked_at = None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.reject",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(
                period=period,
                entry_count=len(entries),
                total_hours=self._sum_entry_hours(entries),
            ),
        )
        return period

    def lock_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriod:
        require_permission(self._user_session, "settings.manage", operation_label="lock timesheet period")
        period = self._get_or_create_timesheet_period(resource_id=resource_id, period_start=period_start)
        if period.status == TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Approved timesheet periods are already locked.")
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime.now(timezone.utc)
        period.decision_note = (note or "").strip() or None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        entries = self.list_time_entries_for_resource_period(resource_id, period_start=period.period_start)
        record_audit(
            self,
            action="timesheet_period.lock",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(
                period=period,
                entry_count=len(entries),
                total_hours=self._sum_entry_hours(entries),
            ),
        )
        return period

    def unlock_timesheet_period(self, period_id: str, *, note: str = "") -> TimesheetPeriod:
        require_permission(self._user_session, "settings.manage", operation_label="unlock timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.LOCKED:
            raise ValidationError("Only explicitly locked timesheet periods can be unlocked.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        period.status = TimesheetPeriodStatus.OPEN
        period.locked_at = None
        period.decision_note = (note or "").strip() or None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        record_audit(
            self,
            action="timesheet_period.unlock",
            entity_type="timesheet_period",
            entity_id=period.id,
            details=self._build_timesheet_period_audit_details(
                period=period,
                entry_count=len(entries),
                total_hours=self._sum_entry_hours(entries),
            ),
        )
        return period


__all__ = ["TimesheetPeriodsMixin"]
