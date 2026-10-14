from __future__ import annotations

from src.core.modules.project_management.application.financials.invoicing.queries.preparation import (
    ProjectBillingPreparationQueryHandler,
)
from src.core.modules.project_management.application.financials.invoicing.queries.profile import (
    ProjectBillingProfileQueryHandler,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_billing_queries(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> tuple[ProjectBillingProfileQueryHandler, ProjectBillingPreparationQueryHandler]:
    profile_queries = ProjectBillingProfileQueryHandler(
        billing_repo=repositories.pm.project_billing_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    preparation_queries = ProjectBillingPreparationQueryHandler(
        billing_repo=repositories.pm.project_billing_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    return profile_queries, preparation_queries
