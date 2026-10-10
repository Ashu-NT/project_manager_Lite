"""Assemble the Platform enterprise-calendar services and shared resolver."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.core.platform.application.history.activity import ActivityService
from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.application.time_management.calendar.assignment.calendar_assignment_service import (
    CalendarAssignmentService,
)
from src.core.platform.application.time_management.calendar.capacity.global_calendar_shim import (
    GlobalCalendarShim,
)
from src.core.platform.application.time_management.calendar.capacity.platform_calendar_resolver import (
    PlatformCalendarResolver,
)
from src.core.platform.application.time_management.calendar.capacity.working_time_calculator import (
    WorkingTimeCalculator,
)
from src.core.platform.application.time_management.calendar.definitions.calendar_exception_service import (
    CalendarExceptionService,
)
from src.core.platform.application.time_management.calendar.definitions.recurring_event_service import (
    RecurringEventService,
)
from src.core.platform.application.time_management.calendar.definitions.shift_pattern_service import (
    ShiftPatternService,
)
from src.core.platform.application.time_management.calendar.definitions.working_rule_service import (
    WorkingRuleService,
)
from src.core.platform.application.time_management.calendar.platform_calendar_service import (
    PlatformCalendarService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.infra.composition.persistence.repositories import RepositoryBundle

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CalendarDependencies:
    working_time_calculator: WorkingTimeCalculator
    platform_calendar_service: PlatformCalendarService
    platform_calendar_resolver: PlatformCalendarResolver
    working_rule_service: WorkingRuleService
    calendar_exception_service: CalendarExceptionService
    recurring_event_service: RecurringEventService
    shift_pattern_service: ShiftPatternService
    calendar_assignment_service: CalendarAssignmentService
    global_calendar_shim: GlobalCalendarShim


def build_calendar_dependencies(
    *,
    session: Session,
    repositories: RepositoryBundle,
    user_session: UserSessionContext,
    tenant_context_service: TenantContextService,
    activity_service: ActivityService,
) -> CalendarDependencies:
    working_time_calculator = WorkingTimeCalculator()
    platform_calendar_service = PlatformCalendarService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        organization_repo=repositories.organization_repo,
        rule_repo=repositories.calendar_working_rule_repo,
        exception_repo=repositories.calendar_exception_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        activity_service=activity_service,
    )

    def _get_active_org_id() -> str:
        return tenant_context_service.get_active_organization_id() or ""

    # This process-lifetime resolver must share its cache with write-side invalidation.
    platform_calendar_resolver = PlatformCalendarResolver(
        organization_id=_get_active_org_id(),
        calendar_repo=repositories.platform_calendar_repo,
        rule_repo=repositories.calendar_working_rule_repo,
        exception_repo=repositories.calendar_exception_repo,
        recurring_repo=repositories.calendar_recurring_event_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        project_assignment_repo=repositories.project_calendar_assignment_repo,
        resource_assignment_repo=repositories.resource_calendar_assignment_repo,
        calculator=working_time_calculator,
        shift_pattern_repo=repositories.shift_pattern_repo,
    )
    working_rule_service = WorkingRuleService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        rule_repo=repositories.calendar_working_rule_repo,
        user_session=user_session,
        on_calendar_data_changed=platform_calendar_resolver.invalidate_cache,
    )
    calendar_exception_service = CalendarExceptionService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        exception_repo=repositories.calendar_exception_repo,
        user_session=user_session,
    )
    recurring_event_service = RecurringEventService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        event_repo=repositories.calendar_recurring_event_repo,
        user_session=user_session,
        on_calendar_data_changed=platform_calendar_resolver.invalidate_cache,
    )
    shift_pattern_service = ShiftPatternService(
        session=session,
        pattern_repo=repositories.shift_pattern_repo,
        organization_repo=repositories.organization_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        on_calendar_data_changed=platform_calendar_resolver.invalidate_cache,
    )
    calendar_assignment_service = CalendarAssignmentService(
        session=session,
        calendar_repo=repositories.platform_calendar_repo,
        assignment_repo=repositories.calendar_assignment_repo,
        project_assignment_repo=repositories.project_calendar_assignment_repo,
        resource_assignment_repo=repositories.resource_calendar_assignment_repo,
        user_session=user_session,
        activity_service=activity_service,
    )
    global_calendar_shim = GlobalCalendarShim(resolver=platform_calendar_resolver)
    # Existing organizations may predate creation-time default calendar setup.
    try:
        org = tenant_context_service.get_active_organization()
        if org:
            logger.debug("Ensuring platform global calendar organization_id=%s", org.id)
            platform_calendar_service.ensure_global_calendar(org.id)
            logger.debug("Platform global calendar ensured organization_id=%s", org.id)
    except Exception:
        logger.exception("Enterprise global calendar bootstrap failed; continuing startup")

    return CalendarDependencies(
        working_time_calculator=working_time_calculator,
        platform_calendar_service=platform_calendar_service,
        platform_calendar_resolver=platform_calendar_resolver,
        working_rule_service=working_rule_service,
        calendar_exception_service=calendar_exception_service,
        recurring_event_service=recurring_event_service,
        shift_pattern_service=shift_pattern_service,
        calendar_assignment_service=calendar_assignment_service,
        global_calendar_shim=global_calendar_shim,
    )
