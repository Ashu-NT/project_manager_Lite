from __future__ import annotations

from src.core.modules.project_management.application.financials.budgets.queries.catalog import (
    BudgetQueries,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_budget_query(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> BudgetQueries:
    return BudgetQueries(
        budget_repo=repositories.pm.project_budget_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
