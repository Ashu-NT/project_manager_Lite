from __future__ import annotations

from src.core.modules.project_management.application.financials.commitments.queries import (
    ProjectCommitmentQueryHandler,
)
from src.core.modules.project_management.application.financials.cost.entries.queries import (
    ProjectCostEntryQueryHandler,
)
from src.core.modules.project_management.application.financials.planned_costs.queries import (
    PlannedCostQueryHandler,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_cost_queries(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> tuple[
    ProjectCostEntryQueryHandler, ProjectCommitmentQueryHandler, PlannedCostQueryHandler
]:
    cost_entry_queries = ProjectCostEntryQueryHandler(
        entry_repo=repositories.pm.project_cost_entry_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    commitment_queries = ProjectCommitmentQueryHandler(
        commitment_repo=repositories.pm.project_commitment_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    planned_cost_queries = PlannedCostQueryHandler(
        planned_cost_repo=repositories.pm.planned_cost_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )
    return cost_entry_queries, commitment_queries, planned_cost_queries
