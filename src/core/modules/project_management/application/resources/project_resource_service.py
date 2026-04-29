from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.resources.commands.project_resource_commands import (
    ProjectResourceCommandMixin,
)
from src.core.modules.project_management.application.resources.queries.project_resource_queries import (
    ProjectResourceQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin


class ProjectResourceService(
    ProjectManagementModuleGuardMixin,
    ProjectResourceCommandMixin,
    ProjectResourceQueryMixin,
):
    """Project-resource membership application service orchestrator."""

    def __init__(
        self,
        project_resource_repo: ProjectResourceRepository,
        resource_repo: ResourceRepository,
        session: Session,
        user_session=None,
        audit_service=None,
        module_catalog_service=None,
    ):
        self._project_resource_repo: ProjectResourceRepository = project_resource_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._session: Session = session
        self._user_session = user_session
        self._audit_service = audit_service
        self._module_catalog_service = module_catalog_service


__all__ = ["ProjectResourceService"]
