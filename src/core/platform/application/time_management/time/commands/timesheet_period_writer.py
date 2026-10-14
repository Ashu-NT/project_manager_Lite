from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.application.time_management.time.commands.approved_time_events import (
    ApprovedTimeEventPublisher,
)
from src.core.platform.application.time_management.time.queries.timesheet_period_query import (
    TimesheetPeriodAggregate,
    TimesheetPeriodQueryHandler,
)
from src.core.platform.application.time_management.time.timesheet_events import (
    TimesheetPeriodStatusChanged,
    TimesheetPeriodStatusChangeType,
)
from src.core.platform.application.time_management.time.timesheet_support import (
    TimesheetSupport,
)
from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimesheetPeriodRepository,
    WorkResourceRepository,
)
from src.core.platform.contract.uow.time_management.time_unit_of_work import (
    TimeUnitOfWorkFactory,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.domain.time_management.time import (
    TimeEntry,
    TimesheetPeriod,
    TimesheetPeriodStatus,
)
from src.core.shared.activity import record_activity
from src.core.shared.audit import record_audit_entry
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_event_publisher import (
    PostCommitEventPublisher,
    TransactionalEventDispatcher,
)

logger = logging.getLogger(__name__)


class TimesheetPeriodTransitionWriter:
    """Persists one already-validated TimesheetPeriod transition in one Time UoW.

    CAS status/version transition, optional Approved Time outbox staging,
    audit, activity and `TimesheetPeriodStatusChanged` commit together. The
    immediate financial dispatch runs only after commit and only when Approved
    Time events were staged; a dispatch failure never undoes the commit.
    """

    def __init__(
        self,
        *,
        session: Session,
        support: TimesheetSupport,
        period_queries: TimesheetPeriodQueryHandler,
        approved_time_events: ApprovedTimeEventPublisher,
        resource_repo: WorkResourceRepository,
        timesheet_period_repo: TimesheetPeriodRepository | None,
        uow_factory: TimeUnitOfWorkFactory,
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
        tenant_context_service: TenantContextService | None,
        user_session: UserSessionContext | None,
        enterprise_audit_service: Any = None,
    ) -> None:
        self._session = session
        self._support = support
        self._period_queries = period_queries
        self._approved_time_events = approved_time_events
        self._resource_repo = resource_repo
        self._timesheet_period_repo = timesheet_period_repo
        self._uow_factory = uow_factory
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        # Read by record_audit_entry(self, ...).
        self._enterprise_audit_service = enterprise_audit_service
        self._approved_time_dispatcher: Callable[[], None] | None = None

    def set_approved_time_dispatcher(self, dispatcher: Callable[[], None] | None) -> None:
        self._approved_time_dispatcher = dispatcher

    def require_period(self, period_id: str) -> TimesheetPeriod:
        if self._timesheet_period_repo is None:
            raise NotFoundError(
                "Timesheet period repository is not configured.",
                code="TIMESHEET_PERIOD_REPO_MISSING",
            )
        period = self._timesheet_period_repo.get(period_id)
        if not period:
            raise NotFoundError("Timesheet period not found.", code="TIMESHEET_PERIOD_NOT_FOUND")
        return period

    @staticmethod
    def require_current_version(period: TimesheetPeriod, expected_version: int) -> None:
        if expected_version < 1 or period.version != expected_version:
            raise ConcurrencyError(
                "Timesheet period changed since it was loaded. Refresh and try again.",
                code="TIMESHEET_PERIOD_STALE",
            )

    def persist_transition(
        self,
        *,
        period: TimesheetPeriod,
        expected_status: TimesheetPeriodStatus,
        expected_version: int,
        action: str,
        change_type: TimesheetPeriodStatusChangeType,
        entries: list[TimeEntry],
        severity: str,
        enqueue_approved_time: bool = False,
    ) -> TimesheetPeriodAggregate:
        project_ids = self._support.project_ids_for_entries(entries)
        emitted_count = 0
        principal = getattr(self._user_session, "principal", None)
        if self._tenant_context_service is None:
            raise RuntimeError("Timesheet period transitions require the tenant context service.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="mutate timesheet period"
        )
        if self._timesheet_period_repo is None:
            raise NotFoundError(
                "Timesheet period repository is not configured.",
                code="TIMESHEET_PERIOD_REPO_MISSING",
            )
        period_repo = self._timesheet_period_repo

        with self._uow_factory.create(
            session=self._session,
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
            context=DomainEventContext(correlation_id=generate_id()),
        ) as uow:
            period = period_repo.transition(
                period,
                expected_status=expected_status,
                expected_version=expected_version,
            )
            if enqueue_approved_time:
                emitted_count = self._approved_time_events.enqueue_approved_time_events(
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
                category="APPROVAL",
                changed_fields={
                    "status": {"before": expected_status.value, "after": period.status.value},
                },
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
                    **self._build_audit_details(
                        period=period,
                        entry_count=len(entries),
                        total_hours=self._support.sum_entry_hours(entries),
                        project_ids=project_ids,
                    ),
                },
                commit=False,
                fail_closed=True,
            )
            record_activity(
                self,
                action=f"timesheet_period.{action}",
                entity_type="timesheet_period",
                entity_id=period.id,
                module="platform",
                organization_id=period.organization_id,
                details={
                    "transition": f"{expected_status.value}->{period.status.value}",
                    "project_id": project_ids[0] if len(project_ids) == 1 else None,
                },
                commit=False,
            )
            uow.record_event(
                TimesheetPeriodStatusChanged(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    period_id=period.id,
                    resource_id=period.resource_id,
                    change_type=change_type,
                    project_ids=tuple(project_ids),
                    occurred_at=datetime.now(UTC),
                )
            )
            uow.commit()

        dispatcher = self._approved_time_dispatcher
        if callable(dispatcher) and emitted_count:
            try:
                dispatcher()
            except Exception:
                logger.exception(
                    "Approved Time was committed but immediate financial dispatch failed"
                )
        return self._period_queries.build_timesheet_period_aggregate(
            resource_id=period.resource_id,
            period_start=period.period_start,
            period=period,
            entries=entries,
        )

    def _build_audit_details(
        self,
        *,
        period: TimesheetPeriod,
        entry_count: int,
        total_hours: float,
        project_ids: list[str] | None = None,
    ) -> dict[str, object]:
        resource = self._resource_repo.get(period.resource_id)
        details: dict[str, object] = {
            "resource_name": resource.name if resource is not None else period.resource_id,
            "period_start": str(period.period_start),
            "period_end": str(period.period_end),
            "status": period.status.value,
            "entry_count": entry_count,
            "total_hours": total_hours,
        }
        normalized_project_ids = [item for item in (project_ids or []) if str(item).strip()]
        if len(normalized_project_ids) == 1:
            details["project_id"] = normalized_project_ids[0]
        elif normalized_project_ids:
            details["project_ids"] = normalized_project_ids
        return details


__all__ = ["TimesheetPeriodTransitionWriter"]
