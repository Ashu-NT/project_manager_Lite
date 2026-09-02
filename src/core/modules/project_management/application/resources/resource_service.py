from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.resources.commands.resource_commands import (
    ResourceCommandMixin,
)
from src.core.modules.project_management.application.resources.commands.skill_commands import (
    SkillCommandMixin,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryMixin,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    SkillQueryMixin,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceCatalogReader,
    ResourceInspectorReader,
    ResourceSummaryReader,
    ResourceActivityReader,
    ResourceAssignmentsReader,
    ResourceProjectsReader,
    ResourceCapabilityReader,
)
from src.core.modules.project_management.contracts.repositories.resources.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import AssignmentRepository
from src.core.modules.project_management.contracts.uow.resources.resource_unit_of_work import (
    ResourceUnitOfWorkFactory,
)
from src.core.platform.contract.repositories.time_management.time.contracts import TimeEntryRepository
from src.core.platform.contract.repositories.master_data.employee.contracts import EmployeeRepository
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


class ResourceService(
    ProjectManagementModuleGuardMixin,
    ResourceCommandMixin,
    ResourceQueryMixin,
    ResourceContextQueryMixin,
    SkillCommandMixin,
    SkillQueryMixin,
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
        skill_repo: ResourceSkillRepository | None = None,
        cert_repo: ResourceCertificationRepository | None = None,
        user_session=None,
        activity_service=None,
        module_catalog_service=None,
        tenant_context_service=None,
        resource_catalog_reader: ResourceCatalogReader | None = None,
        resource_inspector_reader: ResourceInspectorReader | None = None,
        resource_summary_reader: ResourceSummaryReader | None = None,
        resource_projects_reader: ResourceProjectsReader | None = None,
        resource_assignments_reader: ResourceAssignmentsReader | None = None,
        resource_activity_reader: ResourceActivityReader | None = None,
        resource_capability_reader: ResourceCapabilityReader | None = None,
        department_service=None,
        site_service=None,
        uow_factory: ResourceUnitOfWorkFactory | None = None,
        clock: Clock | None = None,
    ):
        self._session: Session = session
        self._resource_repo: ResourceRepository = resource_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._project_resource_repo: ProjectResourceRepository | None = project_resource_repo
        self._time_entry_repo: TimeEntryRepository | None = time_entry_repo
        self._employee_repo: EmployeeRepository | None = employee_repo
        self._skill_repo: ResourceSkillRepository | None = skill_repo
        self._cert_repo: ResourceCertificationRepository | None = cert_repo
        self._user_session = user_session
        self._activity_service = activity_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._resource_catalog_reader = resource_catalog_reader
        self._resource_inspector_reader = resource_inspector_reader
        self._resource_summary_reader = resource_summary_reader
        self._resource_projects_reader = resource_projects_reader
        self._resource_assignments_reader = resource_assignments_reader
        self._resource_activity_reader = resource_activity_reader
        self._resource_capability_reader = resource_capability_reader
        self._department_service = department_service
        self._site_service = site_service
        self._uow_factory: ResourceUnitOfWorkFactory | None = uow_factory
        self._clock: Clock | None = clock

    def _require_uow_factory(self) -> ResourceUnitOfWorkFactory:
        if self._uow_factory is None:
            raise RuntimeError("Resource unit of work is not configured.")
        return self._uow_factory

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


__all__ = ["ResourceService"]
