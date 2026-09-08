from __future__ import annotations

from datetime import date, datetime, timezone
import logging

from src.core.shared.audit import record_audit_entry
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import BusinessRuleError, ConcurrencyError, ValidationError
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.platform.application.time_management.time.timesheet_events import (
    TimesheetPeriodStatusChangeType,
    TimesheetPeriodStatusChanged,
)
from src.core.platform.domain.time_management.time import TimesheetPeriod, TimesheetPeriodStatus
from src.core.platform.application.time_management.time.timesheet_query import TimesheetPeriodAggregate
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkBase


logger = logging.getLogger(__name__)


class TimesheetPeriodsMixin:
    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        expected_version: int | None = None,
        note: str = "",
        _required_permission: str = "timesheet.submit",
    ) -> TimesheetPeriodAggregate:
        if _required_permission not in {"timesheet.submit", "timesheet.submit_on_behalf"}:
            raise BusinessRuleError(
                "Timesheet submission permission is invalid.",
                code="TIMESHEET_SUBMIT_PERMISSION_INVALID",
            )
        require_permission(
            self._user_session,
            _required_permission,
            operation_label="submit timesheet period",
        )
        entries = self.list_time_entries_for_resource_period(
            resource_id, period_start=period_start
        )
        if not entries:
            raise ValidationError("Cannot submit an empty timesheet period.")
        period = self._get_or_create_timesheet_period(
            resource_id=resource_id, period_start=period_start
        )
        if expected_version is not None:
            self._require_current_period_version(period, expected_version)
        if period.status in {
            TimesheetPeriodStatus.SUBMITTED,
            TimesheetPeriodStatus.APPROVED,
            TimesheetPeriodStatus.LOCKED,
        }:
            raise ValidationError(
                f"Timesheet period {period.period_start.isoformat()} is already "
                f"{period.status.value.lower()}."
            )
        previous_status = period.status
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.SUBMITTED
        period.submitted_at = datetime.now(timezone.utc)
        period.submitted_by_user_id = getattr(principal, "user_id", None)
        period.submitted_by_username = getattr(principal, "username", None)
        period.decided_at = None
        period.decided_by_user_id = None
        period.decided_by_username = None
        period.decision_note = str(note or "").strip() or None
        period.locked_at = None
        return self._persist_timesheet_transition(
            period=period,
            expected_status=previous_status,
            expected_version=(period.version if expected_version is None else expected_version),
            action="timesheet_period.submit",
            change_type=TimesheetPeriodStatusChangeType.SUBMITTED,
            entries=entries,
            severity="low",
        )

    def approve_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        require_permission(
            self._user_session,
            "timesheet.approve",
            operation_label="approve timesheet period",
        )
        period = self._require_timesheet_period(period_id)
        self._require_current_period_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be approved.")
        entries = self.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._require_timesheet_review_scope("timesheet.approve", entries)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = str(note or "").strip() or None
        period.locked_at = None
        return self._persist_timesheet_transition(
            period=period,
            expected_status=TimesheetPeriodStatus.SUBMITTED,
            expected_version=expected_version,
            action="timesheet_period.approve",
            change_type=TimesheetPeriodStatusChangeType.APPROVED,
            entries=entries,
            severity="medium",
            enqueue_approved_time=True,
        )

    def reject_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str
    ) -> TimesheetPeriodAggregate:
        require_permission(
            self._user_session,
            "timesheet.approve",
            operation_label="return timesheet period",
        )
        reason = str(note or "").strip()
        if not reason:
            raise ValidationError(
                "A return reason is required.",
                code="TIMESHEET_REVIEW_REASON_REQUIRED",
            )
        period = self._require_timesheet_period(period_id)
        self._require_current_period_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be returned.")
        entries = self.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._require_timesheet_review_scope("timesheet.approve", entries)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime.now(timezone.utc)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = reason
        period.locked_at = None
        return self._persist_timesheet_transition(
            period=period,
            expected_status=TimesheetPeriodStatus.SUBMITTED,
            expected_version=expected_version,
            action="timesheet_period.reject",
            change_type=TimesheetPeriodStatusChangeType.REJECTED,
            entries=entries,
            severity="medium",
        )

    def lock_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        require_permission(
            self._user_session,
            "timesheet.lock",
            operation_label="lock timesheet period",
        )
        period = self._require_timesheet_period(period_id)
        self._require_current_period_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Only approved timesheet periods can be locked.")
        entries = self.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._require_timesheet_review_scope("timesheet.lock", entries)
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime.now(timezone.utc)
        period.decision_note = str(note or "").strip() or period.decision_note
        return self._persist_timesheet_transition(
            period=period,
            expected_status=TimesheetPeriodStatus.APPROVED,
            expected_version=expected_version,
            action="timesheet_period.lock",
            change_type=TimesheetPeriodStatusChangeType.LOCKED,
            entries=entries,
            severity="medium",
        )

    def unlock_timesheet_period(
        self, period_id: str, *, expected_version: int, note: str = ""
    ) -> TimesheetPeriodAggregate:
        require_permission(
            self._user_session,
            "timesheet.lock",
            operation_label="unlock timesheet period",
        )
        period = self._require_timesheet_period(period_id)
        self._require_current_period_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.LOCKED:
            raise ValidationError("Only explicitly locked timesheet periods can be unlocked.")
        entries = self.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._require_timesheet_review_scope("timesheet.lock", entries)
        period.status = TimesheetPeriodStatus.APPROVED
        period.locked_at = None
        period.decision_note = str(note or "").strip() or period.decision_note
        return self._persist_timesheet_transition(
            period=period,
            expected_status=TimesheetPeriodStatus.LOCKED,
            expected_version=expected_version,
            action="timesheet_period.unlock",
            change_type=TimesheetPeriodStatusChangeType.UNLOCKED,
            entries=entries,
            severity="medium",
        )

    def reopen_approved_timesheet_period_for_correction(
        self, period_id: str, *, expected_version: int, note: str
    ) -> TimesheetPeriodAggregate:
        require_permission(
            self._user_session,
            "timesheet.approve",
            operation_label="reopen approved timesheet period for correction",
        )
        reason = str(note or "").strip()
        if not reason:
            raise ValidationError("A correction reason is required.")
        period = self._require_timesheet_period(period_id)
        self._require_current_period_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Only an approved, unlocked timesheet period can be corrected.")
        entries = self.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._require_timesheet_review_scope("timesheet.approve", entries)
        period.status = TimesheetPeriodStatus.OPEN
        period.decision_note = reason
        period.decided_at = None
        period.decided_by_user_id = None
        period.decided_by_username = None
        return self._persist_timesheet_transition(
            period=period,
            expected_status=TimesheetPeriodStatus.APPROVED,
            expected_version=expected_version,
            action="timesheet_period.reopen_for_correction",
            change_type=TimesheetPeriodStatusChangeType.REOPENED_FOR_CORRECTION,
            entries=entries,
            severity="high",
        )

    @staticmethod
    def _require_current_period_version(
        period: TimesheetPeriod, expected_version: int
    ) -> None:
        if expected_version < 1 or period.version != expected_version:
            raise ConcurrencyError(
                "Timesheet period changed since it was loaded. Refresh and try again.",
                code="TIMESHEET_PERIOD_STALE",
            )

    def _require_timesheet_review_scope(
        self, permission_code: str, entries: list
    ) -> None:
        """Extension point for a module-owned scope model such as PM projects."""

    def _persist_timesheet_transition(
        self,
        *,
        period: TimesheetPeriod,
        expected_status: TimesheetPeriodStatus,
        expected_version: int,
        action: str,
        change_type: TimesheetPeriodStatusChangeType,
        entries: list,
        severity: str,
        enqueue_approved_time: bool = False,
    ) -> TimesheetPeriodAggregate:
        project_ids = self._project_ids_for_entries(entries)
        emitted_count = 0
        principal = getattr(self._user_session, "principal", None)
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="mutate timesheet period"
        )

        with SqlAlchemyUnitOfWorkBase(
            session=self._session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=DomainEventContext(correlation_id=generate_id()),
        ) as uow:
            period = self._timesheet_period_repo.transition(  # type: ignore[union-attr]
                period,
                expected_status=expected_status,
                expected_version=expected_version,
            )
            if enqueue_approved_time:
                emitted_count = self._enqueue_approved_time_events(
                    period=period, entries=entries
                )
            record_audit_entry(
                self,
                operation="update",
                entity_type="timesheet_period",
                entity_id=period.id,
                module="platform",
                actor_id=getattr(principal, "user_id", None),
                actor_username=getattr(principal, "username", None),
                organization_id=period.organization_id,
                old_value=expected_status.value,
                new_value=period.status.value,
                severity=severity,
                metadata={
                    "action": action,
                    "transition": f"{expected_status.value}->{period.status.value}",
                    "previous_status": expected_status.value,
                    "new_status": period.status.value,
                    "version": period.version,
                    "reason": period.decision_note,
                    "project_id": project_ids[0] if len(project_ids) == 1 else None,
                    "approved_time_event_count": emitted_count,
                    **self._build_timesheet_period_audit_details(
                        period=period,
                        entry_count=len(entries),
                        total_hours=self._sum_entry_hours(entries),
                        project_ids=project_ids,
                    ),
                },
                commit=False,
                fail_closed=True,
            )
            uow.record_event(
                TimesheetPeriodStatusChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    period_id=period.id,
                    resource_id=period.resource_id,
                    change_type=change_type,
                    project_ids=tuple(project_ids),
                    occurred_at=datetime.now(timezone.utc),
                )
            )
            uow.commit()

        for project_id in project_ids:
            domain_events.tasks_changed.emit(project_id)
        dispatcher = getattr(self, "_approved_time_dispatcher", None)
        if callable(dispatcher) and emitted_count:
            try:
                dispatcher()
            except Exception:
                logger.exception(
                    "Approved Time was committed but immediate financial dispatch failed"
                )
        return self._build_timesheet_period_aggregate(
            resource_id=period.resource_id,
            period_start=period.period_start,
            period=period,
            entries=entries,
        )


__all__ = ["TimesheetPeriodsMixin"]
