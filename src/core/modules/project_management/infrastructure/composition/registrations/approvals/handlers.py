from __future__ import annotations

from src.core.modules.project_management.infrastructure.approval.baseline_apply_participant import (
    BaselineApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.approval.task_apply_participant import (
    TaskApprovalParticipant,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.baseline import (
    build_baseline_approval_deps,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.finance.handlers import (
    register_finance_approval_handlers,
)
from src.core.modules.project_management.infrastructure.composition.registrations.approvals.task import (
    build_task_approval_deps,
)


def register_project_management_approval_handlers(
    *,
    approval_service,
    user_session=None,
    session=None,
    tenant_context_service=None,
    module_catalog_service=None,
    work_calendar_engine=None,
    platform_calendar_resolver=None,
    calendar_assignment_service=None,
    financial_period_service=None,
) -> None:
    from src.core.modules.project_management.contracts.approval import (
        pm_reviewer_permission,
    )

    def register_apply(request_type, handler, *, dependencies_factory):
        approval_service.register_apply_handler(
            request_type, handler, dependencies_factory=dependencies_factory,
            reviewer_permission=pm_reviewer_permission(request_type),
        )

    baseline_participant = BaselineApprovalParticipant()
    register_apply(
        "baseline.create",
        baseline_participant.apply,
        dependencies_factory=lambda uow_session: build_baseline_approval_deps(
            uow_session,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            module_catalog_service=module_catalog_service,
            calendar=work_calendar_engine,
        ),
    )

    task_participant = TaskApprovalParticipant()
    task_dependencies_factory = lambda uow_session: build_task_approval_deps(
        uow_session,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        module_catalog_service=module_catalog_service,
        work_calendar_engine=work_calendar_engine,
        platform_calendar_resolver=platform_calendar_resolver,
        calendar_assignment_service=calendar_assignment_service,
    )
    register_apply(
        "dependency.add",
        task_participant.apply_dependency_add,
        dependencies_factory=task_dependencies_factory,
    )
    register_apply(
        "dependency.remove",
        task_participant.apply_dependency_remove,
        dependencies_factory=task_dependencies_factory,
    )
    register_apply(
        "dependency.update",
        task_participant.apply_dependency_update,
        dependencies_factory=task_dependencies_factory,
    )
    register_apply(
        "task.constraint.update",
        task_participant.apply_task_constraint_update,
        dependencies_factory=task_dependencies_factory,
    )
    register_apply(
        "scheduling.leveling.apply",
        task_participant.apply_resource_leveling_plan,
        dependencies_factory=task_dependencies_factory,
    )

    register_finance_approval_handlers(
        register_apply=register_apply,
        approval_service=approval_service,
        user_session=user_session,
        tenant_context_service=tenant_context_service,
        module_catalog_service=module_catalog_service,
        work_calendar_engine=work_calendar_engine,
        financial_period_service=financial_period_service,
    )


