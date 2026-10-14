from __future__ import annotations

from src.core.modules.project_management.application.financials.forecasts.queries.catalog import (
    ForecastVersionQueries,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_forecast_version_query(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> ForecastVersionQueries:
    return ForecastVersionQueries(
        forecast_repo=repositories.pm.project_forecast_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
