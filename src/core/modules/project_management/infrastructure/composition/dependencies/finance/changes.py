from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.financial_changes.queries.catalog import (
    FinancialChangeQueryHandler,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks.commands.approved_schedule_change import (
    ApprovedScheduleChangeHandler,
)
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    wire_tenant_context_service,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.projects.project import (
    SqlAlchemyProjectRepository,
    SqlAlchemyProjectResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.resources.resource import (
    SqlAlchemyResourceRepository,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.tasks.task import (
    SqlAlchemyAssignmentRepository,
    SqlAlchemyDependencyRepository,
    SqlAlchemyTaskRepository,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.core.platform.infrastructure.persistence.repositories.history.activity.activity import (
    SqlAlchemyActivityRepository,
)
from src.core.platform.infrastructure.persistence.repositories.history.audit.audit_entry import (
    SqlAlchemyAuditRepository,
)


def build_financial_change_queries(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> FinancialChangeQueryHandler:
    return FinancialChangeQueryHandler(
        change_repo=repositories.pm.financial_change_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )


def build_financial_change_schedule_port(
    session: Session,
    *,
    user_session: UserSessionContext | None,
    tenant_context_service: TenantContextService,
    work_calendar_engine: CalendarProtocol,
) -> ApprovedScheduleChangeHandler:
    """Build only the trusted scheduling graph on the caller-owned session."""
    task_repo = wire_tenant_context_service(
        SqlAlchemyTaskRepository(session), tenant_context_service
    )
    dependency_repo = wire_tenant_context_service(
        SqlAlchemyDependencyRepository(session), tenant_context_service
    )
    assignment_repo = wire_tenant_context_service(
        SqlAlchemyAssignmentRepository(session), tenant_context_service
    )
    resource_repo = wire_tenant_context_service(
        SqlAlchemyResourceRepository(session), tenant_context_service
    )
    project_repo = wire_tenant_context_service(
        SqlAlchemyProjectRepository(session), tenant_context_service
    )
    project_resource_repo = wire_tenant_context_service(
        SqlAlchemyProjectResourceRepository(session), tenant_context_service
    )
    audit_repo = wire_tenant_context_service(
        SqlAlchemyAuditRepository(session), tenant_context_service
    )
    activity_repo = wire_tenant_context_service(
        SqlAlchemyActivityRepository(session), tenant_context_service
    )
    audit_service = EnterpriseAuditService(
        session=session,
        audit_repo=audit_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    activity_service = ActivityService(
        session=session,
        activity_repo=activity_repo,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
    )
    scheduling_engine = SchedulingEngine(
        session,
        task_repo,
        dependency_repo,
        work_calendar_engine,
        assignment_repo=assignment_repo,
        resource_repo=resource_repo,
    )
    task_uow_scope = TaskUowScope(
        factory=None,
        tasks=task_repo,
        assignments=assignment_repo,
        dependencies=dependency_repo,
        project_resources=project_resource_repo,
        time_entries=None,
        enterprise_audit_service=audit_service,
        activity_service=activity_service,
    )
    validation_policy = TaskValidationPolicy(
        task_repo=task_repo,
        assignment_repo=assignment_repo,
        resource_repo=resource_repo,
        project_repo=project_repo,
        availability_service=None,
    )
    schedule_synchronizer = TaskScheduleSynchronizer(
        scheduling_engine=scheduling_engine,
        task_repo=task_repo,
    )
    return ApprovedScheduleChangeHandler(
        task_repo=task_repo,
        tenant_context_service=tenant_context_service,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        schedule_synchronizer=schedule_synchronizer,
        validation_policy=validation_policy,
        uow_scope=task_uow_scope,
    )
