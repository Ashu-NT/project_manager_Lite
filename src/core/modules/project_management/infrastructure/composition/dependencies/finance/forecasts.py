from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.financials import (
    ForecastGenerationService,
    ForecastVersionService,
)
from src.infra.composition.modules.platform_registry import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle


def build_forecast_services(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    clock: SystemClock,
) -> tuple[ForecastVersionService, ForecastGenerationService]:
    version_service = ForecastVersionService(
        session=session,
        forecast_repo=repositories.project_forecast_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    generation_service = ForecastGenerationService(
        session=session,
        forecast_repo=repositories.project_forecast_repo,
        project_repo=repositories.project_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        task_repo=repositories.task_repo,
        planned_cost_repo=repositories.planned_cost_repo,
        commitment_repo=repositories.project_commitment_repo,
        cost_entry_repo=repositories.project_cost_entry_repo,
        register_repo=repositories.register_repo,
        clock=clock,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
    return version_service, generation_service
