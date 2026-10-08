from __future__ import annotations

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateMixin,
)
from src.core.modules.project_management.application.projects.commands.deletion import (
    ProjectDeletionMixin,
)
from src.core.modules.project_management.application.projects.commands.status import (
    ProjectStatusMixin,
)
from src.core.modules.project_management.application.projects.commands.update import (
    ProjectUpdateMixin,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryMixin,
)
from src.core.modules.project_management.contracts.reads.projects import (
    ProjectCatalogReader,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    DependencyRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.uow.projects.project_unit_of_work import (
    ProjectUnitOfWorkFactory,
)
from src.core.platform.application.history.activity.activity_service import (
    ActivityService,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.master_data.department.contracts import (
    DepartmentRepository,
)
from src.core.platform.contract.repositories.master_data.party.contracts import (
    PartyRepository,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.platform.domain.master_data.party import PartyLifecycleStatus
from src.core.platform.domain.security.auth.session import UserSessionContext
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.persistence.unit_of_work import UnitOfWorkFactory


class ProjectService(
    ProjectManagementModuleGuardMixin,
    ProjectCreateMixin,
    ProjectUpdateMixin,
    ProjectStatusMixin,
    ProjectDeletionMixin,
    ProjectQueryMixin,
):
    """Project application service orchestrator."""

    def __init__(
        self,
        session: Session,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        dependency_repo: DependencyRepository,
        assignment_repo: AssignmentRepository,
        time_entry_repo: TimeEntryRepository | None,
        user_session: UserSessionContext | None = None,
        activity_service: ActivityService | None = None,
        enterprise_audit_service=None,
        module_catalog_service=None,
        tenant_context_service: TenantContextService | None =None,
        project_catalog_reader: ProjectCatalogReader | None = None,
        uow_factory: ProjectUnitOfWorkFactory | None = None,
        shared_uow_factory: UnitOfWorkFactory | None = None,
        party_repo: PartyRepository | None = None,
        department_repo: DepartmentRepository | None = None,
    ):
        self._session: Session = session
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._dependency_repo: DependencyRepository = dependency_repo
        self._assignment_repo: AssignmentRepository = assignment_repo
        self._time_entry_repo = time_entry_repo
        self._user_session: UserSessionContext | None = user_session
        self._activity_service: ActivityService | None = activity_service
        self._enterprise_audit_service = enterprise_audit_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._project_catalog_reader = project_catalog_reader
        self._uow_factory: ProjectUnitOfWorkFactory | None = uow_factory
        self._shared_uow_factory = shared_uow_factory
        self._party_repo = party_repo
        self._department_repo = department_repo

    def _validate_department_reference(
        self, department_id: str | None, organization_id: str
    ) -> None:
        if not department_id:
            return
        if self._department_repo is None:
            raise RuntimeError("Department directory is not configured.")
        department = self._department_repo.get(department_id)
        if department is None or department.organization_id != organization_id:
            raise ValidationError(
                "Selected department was not found in the project organization.",
                code="PROJECT_DEPARTMENT_NOT_FOUND",
            )
        if not department.is_active:
            raise ValidationError(
                "Selected department is inactive.", code="PROJECT_DEPARTMENT_INACTIVE"
            )

    def _validate_client_party(self, party_id: str | None, organization_id: str) -> None:
        if not party_id:
            return
        if self._party_repo is None:
            raise RuntimeError("Party directory is not configured.")
        party = self._party_repo.get(party_id)
        if party is None or party.organization_id != organization_id:
            raise ValidationError(
                "Selected client was not found in the project organization.",
                code="PROJECT_CLIENT_PARTY_NOT_FOUND",
            )
        if party.status != PartyLifecycleStatus.ACTIVE:
            raise ValidationError("Selected client is inactive.", code="PROJECT_CLIENT_PARTY_INACTIVE")

    def _require_shared_uow_factory(self) -> UnitOfWorkFactory:
        if self._shared_uow_factory is None:
            raise RuntimeError("Project write transaction factory is not configured.")
        return self._shared_uow_factory

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)


__all__ = ["ProjectService"]
