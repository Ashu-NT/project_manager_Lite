from __future__ import annotations

from src.core.modules.project_management.application.financials.configuration.queries.catalog import (
    FinancialConfigurationQueryHandler,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_financial_configuration_query(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> FinancialConfigurationQueryHandler:
    return FinancialConfigurationQueryHandler(
        profile_repo=repositories.pm.project_financial_profile_repo,
        cost_code_repo=repositories.pm.project_cost_code_repo,
        project_repo=repositories.pm.project_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
