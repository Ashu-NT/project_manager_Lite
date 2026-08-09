from __future__ import annotations

from src.core.modules.project_management.application.financials.costs.queries.cost_query import (
    CostQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.cost import CostRepository
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


class CostService(
    ProjectManagementModuleGuardMixin,
    CostQueryMixin,
):
    def __init__(
        self,
        cost_repo: CostRepository,
        project_repo: ProjectRepository,
        user_session=None,
        module_catalog_service=None,
    ):
        self._cost_repo: CostRepository = cost_repo
        self._project_repo: ProjectRepository = project_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service


__all__ = ["CostService"]
