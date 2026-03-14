from __future__ import annotations

from sqlalchemy.orm import Session

from core.platform.common.interfaces import CostRepository, ProjectRepository, TaskRepository
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.modules.project_management.services.cost.lifecycle import CostLifecycleMixin
from core.modules.project_management.services.cost.query import CostQueryMixin
from core.modules.project_management.services.cost.support import CostSupportMixin


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


