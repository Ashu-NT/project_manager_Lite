from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials.budgets.budget_service import (
    BudgetService,
)
from src.core.modules.project_management.application.financials.financial_changes.service import (
    FinancialChangeService,
)
from src.core.modules.project_management.application.financials.forecasts.version_service import (
    ForecastVersionService,
)
from src.core.modules.project_management.application.scheduling import SchedulingEngine
from src.core.modules.project_management.application.tasks import TaskService
from src.core.modules.project_management.application.tasks.commands.approved_schedule_change import (
    ApprovedScheduleChangeHandler,
)
from src.core.modules.project_management.application.tasks.commands.assignment import (
    TaskAssignmentCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.deletion import (
    TaskDeletionCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.dependency import (
    TaskDependencyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy import (
    TaskHierarchyCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.hierarchy_support import (
    TaskHierarchyPolicy,
)
from src.core.modules.project_management.application.tasks.commands.identity import (
    TaskCodePolicy,
)
from src.core.modules.project_management.application.tasks.commands.lifecycle import (
    TaskLifecycleCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.progress import (
    TaskProgressCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.resource_leveling_apply import (
    ResourceLevelingCommandHandler,
)
from src.core.modules.project_management.application.tasks.commands.schedule_sync import (
    TaskScheduleSynchronizer,
)
from src.core.modules.project_management.application.tasks.commands.scheduling_constraint import (
    TaskSchedulingConstraintHandler,
)
from src.core.modules.project_management.application.tasks.commands.validation import (
    TaskValidationPolicy,
)
from src.core.modules.project_management.application.tasks.queries.dependency_diagnostics import (
    TaskDependencyDiagnosticsQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.dependency_query import (
    TaskDependencyQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.hierarchy_query import (
    TaskHierarchyQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_detail_page import (
    TaskDetailPageQueryHandler,
)
from src.core.modules.project_management.application.tasks.queries.task_lookup import (
    TaskLookupQueryHandler,
)
from src.core.modules.project_management.application.tasks.task_unit_of_work_scope import (
    TaskUowScope,
)
from src.core.modules.project_management.infrastructure.approval.financial_change_apply_participant import (
    FinancialChangeApprovalDeps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals._shared import (
    build_approval_repository_context,
    build_enterprise_audit_service,
    wire_tenant_context_service,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.contract.port.time_management.calendar.calendar_protocol import (
    CalendarProtocol,
)


def build_financial_change_approval_deps(
    session: Session,
    *,
    user_session,
    tenant_context_service,
    work_calendar_engine: CalendarProtocol,
    module_catalog_service=None,
    record_event=None,
) -> FinancialChangeApprovalDeps:
    bundle = build_approval_repository_context(session, tenant_context_service)
    change_repo = wire_tenant_context_service(bundle.pm.financial_change_repo, tenant_context_service)
    budget_repo = wire_tenant_context_service(bundle.pm.project_budget_repo, tenant_context_service)
    forecast_repo = wire_tenant_context_service(bundle.pm.project_forecast_repo, tenant_context_service)
    project_repo = wire_tenant_context_service(bundle.pm.project_repo, tenant_context_service)
    financial_profile_repo = wire_tenant_context_service(
        bundle.pm.project_financial_profile_repo, tenant_context_service
    )
    cost_code_repo = wire_tenant_context_service(bundle.pm.project_cost_code_repo, tenant_context_service)
    task_repo = wire_tenant_context_service(bundle.pm.task_repo, tenant_context_service)
    dependency_repo = wire_tenant_context_service(bundle.pm.dependency_repo, tenant_context_service)
    assignment_repo = wire_tenant_context_service(bundle.pm.assignment_repo, tenant_context_service)
    resource_repo = wire_tenant_context_service(bundle.pm.resource_repo, tenant_context_service)
    project_resource_repo = wire_tenant_context_service(
        bundle.pm.project_resource_repo, tenant_context_service
    )
    activity_repo = wire_tenant_context_service(bundle.platform.activity_repo, tenant_context_service)

    enterprise_audit_service = build_enterprise_audit_service(
        session,
        bundle,
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
        enterprise_audit_service=enterprise_audit_service,
        activity_service=activity_service,
    )
    hierarchy_policy = TaskHierarchyPolicy(
        task_repo=task_repo,
        assignment_repo=assignment_repo,
        dependency_repo=dependency_repo,
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
    code_policy = TaskCodePolicy(task_repo=task_repo)
    scheduling_constraint_handler = TaskSchedulingConstraintHandler(
        task_repo=task_repo,
        user_session=user_session,
        approval_service=None,
        tenant_context_service=tenant_context_service,
        scheduling_engine=scheduling_engine,
        work_calendar_engine=work_calendar_engine,
        schedule_synchronizer=schedule_synchronizer,
        uow_scope=task_uow_scope,
    )
    lifecycle_handler = TaskLifecycleCommandHandler(
        task_repo=task_repo,
        work_calendar_engine=work_calendar_engine,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        code_policy=code_policy,
        hierarchy_policy=hierarchy_policy,
        validation_policy=validation_policy,
        scheduling_constraint_handler=scheduling_constraint_handler,
        uow_scope=task_uow_scope,
    )
    dependency_diagnostics_handler = TaskDependencyDiagnosticsQueryHandler(
        task_repo=task_repo,
        dependency_repo=dependency_repo,
        work_calendar_engine=work_calendar_engine,
        scheduling_engine=scheduling_engine,
        user_session=user_session,
    )
    task_service = TaskService(
        user_session=user_session,
        module_catalog_service=module_catalog_service,
        task_uow_scope=task_uow_scope,
        deletion_handler=TaskDeletionCommandHandler(
            task_repo=task_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            uow_scope=task_uow_scope,
        ),
        progress_handler=TaskProgressCommandHandler(
            task_repo=task_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            validation_policy=validation_policy,
            uow_scope=task_uow_scope,
        ),
        approved_schedule_change_handler=ApprovedScheduleChangeHandler(
            task_repo=task_repo,
            tenant_context_service=tenant_context_service,
            work_calendar_engine=work_calendar_engine,
            scheduling_engine=scheduling_engine,
            schedule_synchronizer=schedule_synchronizer,
            validation_policy=validation_policy,
            uow_scope=task_uow_scope,
        ),
        hierarchy_command_handler=TaskHierarchyCommandHandler(
            task_repo=task_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            uow_scope=task_uow_scope,
        ),
        scheduling_constraint_handler=scheduling_constraint_handler,
        lifecycle_handler=lifecycle_handler,
        dependency_command_handler=TaskDependencyCommandHandler(
            task_repo=task_repo,
            dependency_repo=dependency_repo,
            user_session=user_session,
            approval_service=None,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            diagnostics_handler=dependency_diagnostics_handler,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        ),
        dependency_query_handler=TaskDependencyQueryHandler(
            task_repo=task_repo,
            dependency_repo=dependency_repo,
            user_session=user_session,
        ),
        assignment_handler=TaskAssignmentCommandHandler(
            task_repo=task_repo,
            assignment_repo=assignment_repo,
            resource_repo=resource_repo,
            project_resource_repo=project_resource_repo,
            time_entry_repo=None,
            employee_repo=None,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            hierarchy_policy=hierarchy_policy,
            validation_policy=validation_policy,
            assignment_skill_validator=None,
            enterprise_resource_availability_service=None,
            uow_scope=task_uow_scope,
            overallocation_policy="warn",
        ),
        resource_leveling_handler=ResourceLevelingCommandHandler(
            task_repo=task_repo,
            assignment_repo=assignment_repo,
            dependency_repo=dependency_repo,
            resource_repo=resource_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=user_session,
            approval_service=None,
            tenant_context_service=tenant_context_service,
            schedule_synchronizer=schedule_synchronizer,
            uow_scope=task_uow_scope,
        ),
        detail_query_handler=TaskDetailPageQueryHandler(
            task_repo=task_repo,
            task_workspace_reader=None,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
        ),
        lookup_query_handler=TaskLookupQueryHandler(
            task_repo=task_repo,
            assignment_repo=assignment_repo,
            user_session=user_session,
        ),
        hierarchy_query_handler=TaskHierarchyQueryHandler(
            task_repo=task_repo,
            work_calendar_engine=work_calendar_engine,
            user_session=user_session,
        ),
    )
    clock = SystemClock()
    budget_authority = BudgetService(
        session=session,
        budget_repo=budget_repo,
        project_repo=project_repo,
        financial_profile_repo=financial_profile_repo,
        cost_code_repo=cost_code_repo,
        task_repo=task_repo,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        approval_service=None,
    )
    forecast_authority = ForecastVersionService(
        session=session,
        forecast_repo=forecast_repo,
        project_repo=project_repo,
        financial_profile_repo=financial_profile_repo,
        cost_code_repo=cost_code_repo,
        task_repo=task_repo,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
        record_event=record_event,
        approval_service=None,
    )
    financial_change_service = FinancialChangeService(
        session=session,
        change_repo=change_repo,
        budget_repo=budget_repo,
        forecast_repo=forecast_repo,
        project_repo=project_repo,
        financial_profile_repo=financial_profile_repo,
        cost_code_repo=cost_code_repo,
        task_repo=task_repo,
        task_service=task_service,
        budget_authority=budget_authority,
        forecast_authority=forecast_authority,
        approval_service=None,
        clock=clock,
        user_session=user_session,
        enterprise_audit_service=enterprise_audit_service,
        module_catalog_service=module_catalog_service,
        tenant_context_service=tenant_context_service,
    )
    return FinancialChangeApprovalDeps(financial_change_service=financial_change_service)


__all__ = ["build_financial_change_approval_deps"]
