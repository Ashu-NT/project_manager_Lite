from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.resources.commands.resource_commands import (
    ResourceCommandMixin,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.task import AssignmentRepository
from src.core.platform.common.interfaces import TimeEntryRepository
from src.core.platform.org.contracts import EmployeeRepository
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


class ResourceService(
    ProjectManagementModuleGuardMixin,
    ResourceCommandMixin,
    ResourceQueryMixin,
):
    """Resource application service orchestrator."""

    def __init__(
        self,
        session: Session,
        resource_repo: ResourceRepository,
        assignment_repo: AssignmentRepository,
        project_resource_repo: ProjectResourceRepository | None = None,
        time_entry_repo: TimeEntryRepository | None = None,
        employee_repo: EmployeeRepository | None = None,
        user_session=None,
        audit_service=None,
        module_catalog_service=None,
    ):
        self._session: Session = session
        self._resource_repo: ResourceRepository = resource_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._project_resource_repo: ProjectResourceRepository | None = project_resource_repo
        self._time_entry_repo: TimeEntryRepository | None = time_entry_repo
        self._employee_repo: EmployeeRepository | None = employee_repo
        self._user_session = user_session
        self._audit_service = audit_service
        self._module_catalog_service = module_catalog_service


__all__ = ["ResourceService"]
