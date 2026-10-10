from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials import (
    ProjectBillingPreparationService,
    ProjectBillingProfileService,
    RateCardResolver,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_billing_services(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    clock: SystemClock,
    rate_resolver: RateCardResolver,
) -> tuple[ProjectBillingProfileService, ProjectBillingPreparationService]:
    profile_service = ProjectBillingProfileService(
        session=session,
        billing_repo=repositories.pm.project_billing_repo,
        financial_profile_repo=repositories.pm.project_financial_profile_repo,
        project_repo=repositories.pm.project_repo,
        tenant_context_service=platform_services.tenant_context_service,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
    )
    preparation_service = ProjectBillingPreparationService(
        session=session,
        billing_repo=repositories.pm.project_billing_repo,
        financial_profile_repo=repositories.pm.project_financial_profile_repo,
        cost_entry_repo=repositories.pm.project_cost_entry_repo,
        labor_posting_repo=repositories.pm.approved_time_labor_posting_repo,
        rate_resolver=rate_resolver,
        financial_period_service=platform_services.financial_period_service,
        tenant_context_service=platform_services.tenant_context_service,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
    )
    return profile_service, preparation_service
