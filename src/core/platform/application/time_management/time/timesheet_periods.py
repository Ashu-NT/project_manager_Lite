from __future__ import annotations

from datetime import date, datetime, timezone
import logging

from src.core.shared.audit import record_audit_entry
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ValidationError
from src.core.shared.events.domain_events import domain_events
from src.core.platform.domain.time_management.time import TimesheetPeriod, TimesheetPeriodStatus
from src.core.platform.application.time_management.time.timesheet_query import (
    TimesheetPeriodAggregate,
)


logger = logging.getLogger(__name__)


class TimesheetPeriodsMixin:
    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodAggregate:
        require_permission(self._user_session, "timesheet.submit", operation_label="submit timesheet period")
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
        period.decision_note = note
        period.locked_at = None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        project_ids = self._project_ids_for_entries(entries)
        record_audit_entry(
            self,
            operation="update",
            entity_type="timesheet_period",
            entity_id=period.id,
            module="platform",
            severity="low",
            metadata={
                "action": "timesheet_period.submit",
                "project_id": project_ids[0] if len(project_ids) == 1 else None,
                **self._build_timesheet_period_audit_details(
                    period=period,
                    entry_count=len(entries),
                    total_hours=self._sum_entry_hours(entries),
                    project_ids=project_ids,
                ),
            },
        )
        self._emit_timesheet_period_events(period.id, project_ids)
        return self._build_timesheet_period_aggregate(
            resource_id=resource_id,
            period_start=period_start,
            period=period,
            entries=entries,
        )

    def approve_timesheet_period(
        self, period_id: str, *, note: str = ""
    ) -> TimesheetPeriodAggregate:
        require_permission(self._user_session, "timesheet.approve", operation_label="approve timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be approved.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = note
        period.locked_at = None
        project_ids = self._project_ids_for_entries(entries)
        try:
            self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
            emitted_count = self._enqueue_approved_time_events(period=period, entries=entries)
            record_audit_entry(
                self,
                operation="update",
                entity_type="timesheet_period",
                entity_id=period.id,
                module="platform",
                severity="medium",
                metadata={
                    "action": "timesheet_period.approve",
                    "project_id": project_ids[0] if len(project_ids) == 1 else None,
                    **self._build_timesheet_period_audit_details(
                        period=period,
                        entry_count=len(entries),
                        total_hours=self._sum_entry_hours(entries),
                        project_ids=project_ids,
                    ),
                    "approved_time_event_count": emitted_count,
                },
                commit=False,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        self._emit_timesheet_period_events(period.id, project_ids)
        dispatcher = getattr(self, "_approved_time_dispatcher", None)
        if callable(dispatcher) and emitted_count:
            try:
                dispatcher()
            except Exception:
                logger.exception("Approved Time was committed but immediate financial dispatch failed")
        return self._build_timesheet_period_aggregate(
            resource_id=period.resource_id,
            period_start=period.period_start,
            period=period,
            entries=entries,
        )

    def reject_timesheet_period(
        self, period_id: str, *, note: str = ""
    ) -> TimesheetPeriodAggregate:
        require_permission(self._user_session, "timesheet.approve", operation_label="reject timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be rejected.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = note
        period.locked_at = None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        project_ids = self._project_ids_for_entries(entries)
        record_audit_entry(
            self,
            operation="update",
            entity_type="timesheet_period",
            entity_id=period.id,
            module="platform",
            severity="medium",
            metadata={
                "action": "timesheet_period.reject",
                "project_id": project_ids[0] if len(project_ids) == 1 else None,
                **self._build_timesheet_period_audit_details(
                    period=period,
                    entry_count=len(entries),
                    total_hours=self._sum_entry_hours(entries),
                    project_ids=project_ids,
                ),
            },
        )
        self._emit_timesheet_period_events(period.id, project_ids)
        return self._build_timesheet_period_aggregate(
            resource_id=period.resource_id,
            period_start=period.period_start,
            period=period,
            entries=entries,
        )

    def lock_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        note: str = "",
    ) -> TimesheetPeriodAggregate:
        require_permission(self._user_session, "timesheet.lock", operation_label="lock timesheet period")
        period = self._get_or_create_timesheet_period(resource_id=resource_id, period_start=period_start)
        if period.status != TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Only approved timesheet periods can be locked.")
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime.now(timezone.utc)
        period.decision_note = note
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        entries = self.list_time_entries_for_resource_period(resource_id, period_start=period.period_start)
        project_ids = self._project_ids_for_entries(entries)
        record_audit_entry(
            self,
            operation="update",
            entity_type="timesheet_period",
            entity_id=period.id,
            module="platform",
            severity="medium",
            metadata={
                "action": "timesheet_period.lock",
                "project_id": project_ids[0] if len(project_ids) == 1 else None,
                **self._build_timesheet_period_audit_details(
                    period=period,
                    entry_count=len(entries),
                    total_hours=self._sum_entry_hours(entries),
                    project_ids=project_ids,
                ),
            },
        )
        self._emit_timesheet_period_events(period.id, project_ids)
        return self._build_timesheet_period_aggregate(
            resource_id=resource_id,
            period_start=period_start,
            period=period,
            entries=entries,
        )

    def unlock_timesheet_period(
        self, period_id: str, *, note: str = ""
    ) -> TimesheetPeriodAggregate:
        require_permission(self._user_session, "timesheet.lock", operation_label="unlock timesheet period")
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.LOCKED:
            raise ValidationError("Only explicitly locked timesheet periods can be unlocked.")
        entries = self.list_time_entries_for_resource_period(period.resource_id, period_start=period.period_start)
        period.status = TimesheetPeriodStatus.APPROVED
        period.locked_at = None
        period.decision_note = note
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        self._session.commit()
        project_ids = self._project_ids_for_entries(entries)
        record_audit_entry(
            self,
            operation="update",
            entity_type="timesheet_period",
            entity_id=period.id,
            module="platform",
            severity="medium",
            metadata={
                "action": "timesheet_period.unlock",
                "project_id": project_ids[0] if len(project_ids) == 1 else None,
                **self._build_timesheet_period_audit_details(
                    period=period,
                    entry_count=len(entries),
                    total_hours=self._sum_entry_hours(entries),
                    project_ids=project_ids,
                ),
            },
        )
        self._emit_timesheet_period_events(period.id, project_ids)
        return self._build_timesheet_period_aggregate(
            resource_id=period.resource_id,
            period_start=period.period_start,
            period=period,
            entries=entries,
        )

    def reopen_approved_timesheet_period_for_correction(
        self, period_id: str, *, note: str
    ) -> TimesheetPeriodAggregate:
        require_permission(
            self._user_session,
            "timesheet.approve",
            operation_label="reopen approved timesheet period for correction",
        )
        period = self._require_timesheet_period(period_id)
        if period.status != TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Only an approved, unlocked timesheet period can be corrected.")
        if not str(note or "").strip():
            raise ValidationError("A correction reason is required.")
        entries = self.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        period.status = TimesheetPeriodStatus.OPEN
        period.decision_note = str(note).strip()
        period.decided_at = None
        period.decided_by_user_id = None
        period.decided_by_username = None
        self._timesheet_period_repo.update(period)  # type: ignore[union-attr]
        project_ids = self._project_ids_for_entries(entries)
        record_audit_entry(
            self,
            operation="update",
            entity_type="timesheet_period",
            entity_id=period.id,
            module="platform",
            severity="high",
            metadata={
                "action": "timesheet_period.reopen_for_correction",
                "reason": period.decision_note,
                **self._build_timesheet_period_audit_details(
                    period=period,
                    entry_count=len(entries),
                    total_hours=self._sum_entry_hours(entries),
                    project_ids=project_ids,
                ),
            },
            commit=False,
        )
        self._session.commit()
        self._emit_timesheet_period_events(period.id, project_ids)
        return self._build_timesheet_period_aggregate(
            resource_id=period.resource_id,
            period_start=period.period_start,
            period=period,
            entries=entries,
        )

    @staticmethod
    def _emit_timesheet_period_events(period_id: str, project_ids: list[str]) -> None:
        domain_events.timesheet_periods_changed.emit(period_id)
        for project_id in project_ids:
            domain_events.tasks_changed.emit(project_id)


__all__ = ["TimesheetPeriodsMixin"]
