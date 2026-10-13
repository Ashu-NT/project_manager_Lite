from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials import (
    PlannedCostService,
    ProjectCommitmentService,
    ProjectCostEntryService,
    RateCardResolver,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_cost_services(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    clock: SystemClock,
    rate_resolver: RateCardResolver,
) -> tuple[ProjectCostEntryService, ProjectCommitmentService, PlannedCostService]:
    cost_entry_service = ProjectCostEntryService(
        session=session,
        entry_repo=repositories.pm.project_cost_entry_repo,
        project_repo=repositories.pm.project_repo,
        financial_profile_repo=repositories.pm.project_financial_profile_repo,
        cost_code_repo=repositories.pm.project_cost_code_repo,
        task_repo=repositories.pm.task_repo,
        resource_repo=repositories.pm.resource_repo,
        financial_period_service=platform_services.financial_period_service,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        approval_service=platform_services.approval_service,
        rate_resolver=rate_resolver,
        labor_posting_repo=repositories.pm.approved_time_labor_posting_repo,
    )
    commitment_service = ProjectCommitmentService(
        session=session,
        commitment_repo=repositories.pm.project_commitment_repo,
        cost_entry_repo=repositories.pm.project_cost_entry_repo,
        project_repo=repositories.pm.project_repo,
        financial_profile_repo=repositories.pm.project_financial_profile_repo,
        cost_code_repo=repositories.pm.project_cost_code_repo,
        task_repo=repositories.pm.task_repo,
        party_repo=repositories.platform.party_repo,
        site_repo=repositories.platform.site_repo,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    planned_cost_service = PlannedCostService(
        session=session,
        planned_cost_repo=repositories.pm.planned_cost_repo,
        project_repo=repositories.pm.project_repo,
        financial_profile_repo=repositories.pm.project_financial_profile_repo,
        cost_code_repo=repositories.pm.project_cost_code_repo,
        task_repo=repositories.pm.task_repo,
        assignment_repo=repositories.pm.assignment_repo,
        project_resource_repo=repositories.pm.project_resource_repo,
        rate_resolver=rate_resolver,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    return cost_entry_service, commitment_service, planned_cost_service
