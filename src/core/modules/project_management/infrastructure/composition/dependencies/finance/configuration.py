from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.configuration.service import (
    FinancialConfigurationService,
)
from src.core.platform.infrastructure.composition.bootstrap import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle


def build_financial_configuration_service(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
) -> FinancialConfigurationService:
    return FinancialConfigurationService(
        session=session,
        profile_repo=repositories.project_financial_profile_repo,
        cost_code_repo=repositories.project_cost_code_repo,
        project_repo=repositories.project_repo,
        user_session=platform_services.user_session,
        enterprise_audit_service=platform_services.enterprise_audit_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
    )
