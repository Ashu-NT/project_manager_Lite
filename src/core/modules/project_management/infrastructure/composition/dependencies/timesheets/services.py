from __future__ import annotations

from typing import cast

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.timesheets import (
    TimesheetReviewQueryHandler,
    TimesheetWorkspaceCommandHandler,
    TimesheetWorkspaceQueryHandler,
    TimesheetWorkspaceScope,
)
from src.core.modules.project_management.application.timesheets.time_access_policy import (
    ProjectTimesheetAccessPolicy,
    build_task_assignment_hours_synced_event,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.timesheets.bundle import (
    TimesheetComposition,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceIdentityReader,
)
from src.core.modules.project_management.infrastructure.persistence.reads.timesheets import (
    SqlAlchemyTimesheetReviewReader,
    SqlAlchemyTimesheetWorkspaceReader,
)
from src.core.platform.application.integration import IntegrationOutboxService
from src.core.platform.application.time_management.time import (
    ApprovedTimeEventPublisher,
    TimeEntryCommandHandler,
    TimeEntryLedgerRecorder,
    TimeEntryQueryHandler,
    TimesheetPeriodQueryHandler,
    TimesheetPeriodTransitionHandler,
    TimesheetPeriodTransitionWriter,
    TimesheetSupport,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    WorkAllocationRepository,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.core.platform.infrastructure.persistence.uow.time_management.time_unit_of_work import (
    SqlAlchemyTimeUnitOfWorkFactory,
)


def build_timesheet_capabilities(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    approved_time_outbox_service: IntegrationOutboxService | None,
) -> TimesheetComposition:
    """Builds the Platform Time handlers with PM's access policy and assignment
    event vocabulary, and the PM-guarded workspace/review handlers over them. All share
    the caller's Session, so Time UoWs keep the existing transaction semantics."""
    # PM TaskAssignments are Time's work allocations. The structural mismatch
    # (Decimal `hours_logged`, assignment_* parameter names) predates this
    # composition and is tolerated by the Time handlers at runtime.
    work_allocation_repo = cast(WorkAllocationRepository, repositories.pm.assignment_repo)
    resource_repo = repositories.pm.resource_repo
    employee_repo = repositories.platform.employee_repo
    time_entry_repo = repositories.platform.time_entry_repo
    timesheet_period_repo = repositories.platform.timesheet_period_repo
    user_session = platform_services.user_session
    tenant_context_service = platform_services.tenant_context_service
    uow_factory = SqlAlchemyTimeUnitOfWorkFactory()

    support = TimesheetSupport(
        work_allocation_repo=work_allocation_repo,
        work_owner_repo=repositories.pm.task_repo,
        resource_repo=resource_repo,
        employee_repo=employee_repo,
        time_entry_repo=time_entry_repo,
        timesheet_period_repo=timesheet_period_repo,
    )
    access_policy = ProjectTimesheetAccessPolicy(
        user_session=user_session,
        resource_repo=resource_repo,
        employee_repo=employee_repo,
        support=support,
    )
    entry_queries = TimeEntryQueryHandler(
        support=support,
        access_policy=access_policy,
        work_allocation_repo=work_allocation_repo,
        time_entry_repo=time_entry_repo,
    )
    period_queries = TimesheetPeriodQueryHandler(
        support=support,
        access_policy=access_policy,
        entry_queries=entry_queries,
        timesheet_period_repo=timesheet_period_repo,
    )
    time_entries = TimeEntryCommandHandler(
        session=session,
        support=support,
        access_policy=access_policy,
        ledger=TimeEntryLedgerRecorder(
            session=session,
            support=support,
            work_allocation_repo=work_allocation_repo,
            time_entry_repo=time_entry_repo,
            uow_factory=uow_factory,
            transactional_dispatcher=platform_services.platform_transactional_dispatcher,
            post_commit_bus=platform_services.platform_post_commit_bus,
            tenant_context_service=tenant_context_service,
            enterprise_audit_service=platform_services.enterprise_audit_service,
            work_allocation_hours_event_factory=build_task_assignment_hours_synced_event,
        ),
        time_entry_repo=time_entry_repo,
        user_session=user_session,
    )
    period_transitions = TimesheetPeriodTransitionHandler(
        session=session,
        support=support,
        entry_queries=entry_queries,
        access_policy=access_policy,
        writer=TimesheetPeriodTransitionWriter(
            session=session,
            support=support,
            period_queries=period_queries,
            approved_time_events=ApprovedTimeEventPublisher(
                outbox_service=approved_time_outbox_service,
                tenant_context_service=tenant_context_service,
                work_allocation_repo=work_allocation_repo,
                support=support,
            ),
            resource_repo=resource_repo,
            timesheet_period_repo=timesheet_period_repo,
            uow_factory=uow_factory,
            transactional_dispatcher=platform_services.platform_transactional_dispatcher,
            post_commit_bus=platform_services.platform_post_commit_bus,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
            enterprise_audit_service=platform_services.enterprise_audit_service,
        ),
        timesheet_period_repo=timesheet_period_repo,
        user_session=user_session,
    )
    module_catalog_service = platform_services.module_catalog_service
    review_reader = SqlAlchemyTimesheetReviewReader(session=session)
    workspace_scope = TimesheetWorkspaceScope(
        workspace_reader=SqlAlchemyTimesheetWorkspaceReader(
            session=session,
            resource_identity_reader=SqlAlchemyResourceIdentityReader(session=session),
        ),
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    workspace_queries = TimesheetWorkspaceQueryHandler(
        scope=workspace_scope,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    workspace_commands = TimesheetWorkspaceCommandHandler(
        scope=workspace_scope,
        time_entries=time_entries,
        period_transitions=period_transitions,
        entry_queries=entry_queries,
        support=support,
        access_policy=access_policy,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    # The concrete review reader also serves the inspector contract.
    review_queries = TimesheetReviewQueryHandler(
        review_reader=review_reader,
        inspector_reader=review_reader,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
        module_catalog_service=module_catalog_service,
    )
    return TimesheetComposition(
        workspace_queries=workspace_queries,
        workspace_commands=workspace_commands,
        review_queries=review_queries,
        time_entries=time_entries,
        period_transitions=period_transitions,
        time_entry_queries=entry_queries,
        period_queries=period_queries,
    )
