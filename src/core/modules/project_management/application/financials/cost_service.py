from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.financials.commands.cost_lifecycle import (
    CostLifecycleMixin,
)
from src.core.modules.project_management.application.financials.cost_support import (
    CostSupportMixin,
)
from src.core.modules.project_management.application.financials.queries.cost_query import (
    CostQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.contracts.repositories.cost_calendar import CostRepository
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


class CostService(
    ProjectManagementModuleGuardMixin,
    CostLifecycleMixin,
    CostQueryMixin,
    CostSupportMixin,
):
    def __init__(
        self,
        session: Session,
        cost_repo: CostRepository,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        user_session=None,
        audit_service=None,
        approval_service=None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._cost_repo: CostRepository = cost_repo
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._user_session = user_session
        self._audit_service = audit_service
        self._approval_service = approval_service
        self._module_catalog_service = module_catalog_service


__all__ = ["CostService"]



