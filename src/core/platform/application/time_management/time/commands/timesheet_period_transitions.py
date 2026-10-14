from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.time_management.time.commands.timesheet_period_writer import (
    TimesheetPeriodTransitionWriter,
)
from src.core.platform.application.time_management.time.queries.time_entry_query import (
    TimeEntryQueryHandler,
)
from src.core.platform.application.time_management.time.queries.timesheet_period_query import (
    TimesheetPeriodAggregate,
)
from src.core.platform.application.time_management.time.timesheet_events import (
    TimesheetPeriodStatusChangeType,
)
from src.core.platform.application.time_management.time.timesheet_support import (
    TimesheetSupport,
)
from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ValidationError,
)
from src.core.platform.contract.port.time_management.time.time_access_policy import (
    TimeAccessPolicy,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimesheetPeriodRepository,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import (
    TimesheetPeriod,
    TimesheetPeriodStatus,
)

SUBMIT_PERMISSIONS = frozenset({"timesheet.submit", "timesheet.submit_on_behalf"})


class TimesheetPeriodTransitionHandler:
    """TimesheetPeriod workflow: submit, approve/return, lock/unlock, reopen.

    Owns permission, review-scope, status and optimistic-version rules; the
    single-UoW persistence of each transition is the injected writer's job.
    """

    def __init__(
        self,
        *,
        session: Session,
        support: TimesheetSupport,
        entry_queries: TimeEntryQueryHandler,
        access_policy: TimeAccessPolicy,
        writer: TimesheetPeriodTransitionWriter,
        timesheet_period_repo: TimesheetPeriodRepository | None,
        user_session: UserSessionContext | None,
    ) -> None:
        self._session = session
        self._support = support
        self._entry_queries = entry_queries
        self._access = access_policy
        self._writer = writer
        self._timesheet_period_repo = timesheet_period_repo
        self._user_session = user_session

    def set_approved_time_dispatcher(self, dispatcher: Callable[[], None] | None) -> None:
        self._writer.set_approved_time_dispatcher(dispatcher)

    def submit_timesheet_period(
        self,
        resource_id: str,
        *,
        period_start: date,
        expected_version: int | None = None,
        note: str = "",
        required_permission: str = "timesheet.submit",
    ) -> TimesheetPeriodAggregate:
        if required_permission not in SUBMIT_PERMISSIONS:
            raise BusinessRuleError(
                "Timesheet submission permission is invalid.",
                code="TIMESHEET_SUBMIT_PERMISSION_INVALID",
            )
        require_permission(
            self._user_session,
            required_permission,
            operation_label="submit timesheet period",
        )
        entries = self._entry_queries.list_time_entries_for_resource_period(
            resource_id, period_start=period_start
        )
        if not entries:
            raise ValidationError("Cannot submit an empty timesheet period.")
        period = self._get_or_create_timesheet_period(
            resource_id=resource_id, period_start=period_start
        )
        if expected_version is not None:
            self._writer.require_current_version(period, expected_version)
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
        period.submitted_at = datetime.now(UTC)
        period.submitted_by_user_id = getattr(principal, "user_id", None)
        period.submitted_by_username = getattr(principal, "username", None)
        period.decided_at = None
        period.decided_by_user_id = None
        period.decided_by_username = None
        period.decision_note = str(note or "").strip() or None
        period.locked_at = None
        return self._writer.persist_transition(
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
        period = self._writer.require_period(period_id)
        self._writer.require_current_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be approved.")
        entries = self._entry_queries.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._access.require_review_scope("timesheet.approve", entries)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.APPROVED
        period.decided_at = datetime.now(UTC)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = str(note or "").strip() or None
        period.locked_at = None
        return self._writer.persist_transition(
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
        period = self._writer.require_period(period_id)
        self._writer.require_current_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.SUBMITTED:
            raise ValidationError("Only submitted timesheet periods can be returned.")
        entries = self._entry_queries.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._access.require_review_scope("timesheet.approve", entries)
        principal = getattr(self._user_session, "principal", None)
        period.status = TimesheetPeriodStatus.REJECTED
        period.decided_at = datetime.now(UTC)
        period.decided_by_user_id = getattr(principal, "user_id", None)
        period.decided_by_username = getattr(principal, "username", None)
        period.decision_note = reason
        period.locked_at = None
        return self._writer.persist_transition(
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
        period = self._writer.require_period(period_id)
        self._writer.require_current_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Only approved timesheet periods can be locked.")
        entries = self._entry_queries.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._access.require_review_scope("timesheet.lock", entries)
        period.status = TimesheetPeriodStatus.LOCKED
        period.locked_at = datetime.now(UTC)
        period.decision_note = str(note or "").strip() or period.decision_note
        return self._writer.persist_transition(
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
        period = self._writer.require_period(period_id)
        self._writer.require_current_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.LOCKED:
            raise ValidationError("Only explicitly locked timesheet periods can be unlocked.")
        entries = self._entry_queries.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._access.require_review_scope("timesheet.lock", entries)
        period.status = TimesheetPeriodStatus.APPROVED
        period.locked_at = None
        period.decision_note = str(note or "").strip() or period.decision_note
        return self._writer.persist_transition(
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
        period = self._writer.require_period(period_id)
        self._writer.require_current_version(period, expected_version)
        if period.status != TimesheetPeriodStatus.APPROVED:
            raise ValidationError("Only an approved, unlocked timesheet period can be corrected.")
        entries = self._entry_queries.list_time_entries_for_resource_period(
            period.resource_id, period_start=period.period_start
        )
        self._access.require_review_scope("timesheet.approve", entries)
        period.status = TimesheetPeriodStatus.OPEN
        period.decision_note = reason
        period.decided_at = None
        period.decided_by_user_id = None
        period.decided_by_username = None
        return self._writer.persist_transition(
            period=period,
            expected_status=TimesheetPeriodStatus.APPROVED,
            expected_version=expected_version,
            action="timesheet_period.reopen_for_correction",
            change_type=TimesheetPeriodStatusChangeType.REOPENED_FOR_CORRECTION,
            entries=entries,
            severity="high",
        )

    def _get_or_create_timesheet_period(self, *, resource_id: str, period_start: date) -> TimesheetPeriod:
        if self._timesheet_period_repo is None:
            raise ValidationError("Timesheet period repository is not configured.")
        normalized_start, normalized_end = self._support.timesheet_period_bounds(period_start)
        period = self._timesheet_period_repo.get_by_resource_period(resource_id, normalized_start)
        if period is not None:
            return period
        period = TimesheetPeriod.create(
            resource_id=resource_id,
            period_start=normalized_start,
            period_end=normalized_end,
        )
        self._timesheet_period_repo.add(period)
        self._session.flush()
        return period


__all__ = ["TimesheetPeriodTransitionHandler"]
