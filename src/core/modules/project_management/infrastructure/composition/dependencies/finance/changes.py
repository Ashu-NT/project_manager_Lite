from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials import (
    FinancialChangeService,
)
from src.core.modules.project_management.application.tasks import TaskService
from src.core.platform.infrastructure.composition.bootstrap import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle


def build_financial_change_service(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    task_service: TaskService,
    clock: SystemClock,
) -> FinancialChangeService:
    return FinancialChangeService(
        session=session,
        change_repo=repositories.financial_change_repo,
        budget_repo=repositories.project_budget_repo,
        forecast_repo=repositories.project_forecast_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        task_service=task_service,
        approval_service=platform_services.approval_service,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
