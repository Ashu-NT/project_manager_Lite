from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.resources.commands.resource_commands import (
    ResourceMasterCommandHandler,
)
from src.core.modules.project_management.application.resources.commands.skill_commands import (
    ResourceCapabilityCommandHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_queries import (
    ResourceQueryMixin,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    ResourceCapabilityQueryHandler,
)
from src.core.modules.project_management.contracts.reads.resources import (
    ResourceActivityReader,
    ResourceActivityReadPage,
    ResourceAssignmentReadPage,
    ResourceAssignmentsReader,
    ResourceCapabilityReader,
    ResourceCatalogReader,
    ResourceCertificationReadPage,
    ResourceInspectorReader,
    ResourceProjectReadPage,
    ResourceProjectsReader,
    ResourceSkillReadPage,
    ResourceSummaryReader,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import (
    ResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.skills import (
    ResourceCertificationRepository,
    ResourceSkillRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
)
from src.core.modules.project_management.contracts.uow.resources.resource_unit_of_work import (
    ResourceUnitOfWorkFactory,
)
from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    ResourceKind,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.resources.resource import Resource
from src.core.modules.project_management.domain.resources.skills import (
    ResourceCertification,
    ResourceSkill,
)
from src.core.platform.common.ids import generate_id
from src.core.platform.contract.repositories.master_data.employee.contracts import (
    EmployeeRepository,
)
from src.core.platform.contract.repositories.time_management.time.contracts import (
    TimeEntryRepository,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.time.clock import Clock


class ResourceService(
    ProjectManagementModuleGuardMixin,
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
        self._master_command = ResourceMasterCommandHandler(
            resource_repo=resource_repo,
            employee_repo=employee_repo,
            department_service=department_service,
            site_service=site_service,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            uow_factory=uow_factory,
        )
        self._capability_command = ResourceCapabilityCommandHandler(
            skill_repo=skill_repo,
            cert_repo=cert_repo,
            user_session=user_session,
            tenant_context_service=tenant_context_service,
            uow_factory=uow_factory,
        )
        self._user_session = user_session
        self._activity_service = activity_service
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._resource_catalog_reader = resource_catalog_reader
        self._resource_inspector_reader = resource_inspector_reader
        self._resource_summary_reader = resource_summary_reader
        self._context_query = ResourceContextQueryHandler(
            resource_projects_reader=resource_projects_reader,
            resource_assignments_reader=resource_assignments_reader,
            resource_activity_reader=resource_activity_reader,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
        )
        self._capability_query = ResourceCapabilityQueryHandler(
            resource_capability_reader=resource_capability_reader,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
        )
        self._uow_factory: ResourceUnitOfWorkFactory | None = uow_factory
        self._clock: Clock | None = clock

    def _require_uow_factory(self) -> ResourceUnitOfWorkFactory:
        if self._uow_factory is None:
            raise RuntimeError("Resource unit of work is not configured.")
        return self._uow_factory

    def _new_context(self, *, causation_id: str | None = None) -> DomainEventContext:
        return DomainEventContext(correlation_id=generate_id(), causation_id=causation_id)

    def query_resource_skills_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        proficiency: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "skillName",
        sort_direction: str = "asc",
    ) -> ResourceSkillReadPage:
        return self._capability_query.query_resource_skills_page(
            resource_id,
            search_text=search_text,
            proficiency=proficiency,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def query_resource_certifications_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        status: str | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "certificationName",
        sort_direction: str = "asc",
    ) -> ResourceCertificationReadPage:
        return self._capability_query.query_resource_certifications_page(
            resource_id,
            search_text=search_text,
            status=status,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def add_resource_skill(
        self,
        resource_id: str,
        skill_code: str,
        skill_name: str,
        proficiency: str = "intermediate",
        notes: str = "",
    ) -> ResourceSkill:
        return self._capability_command.add_resource_skill(
            resource_id, skill_code, skill_name, proficiency, notes
        )

    def update_resource_skill(
        self,
        *,
        skill_id: str,
        expected_version: int,
        skill_code: str,
        skill_name: str,
        proficiency: str = "intermediate",
        notes: str = "",
    ) -> ResourceSkill:
        return self._capability_command.update_resource_skill(
            skill_id=skill_id,
            expected_version=expected_version,
            skill_code=skill_code,
            skill_name=skill_name,
            proficiency=proficiency,
            notes=notes,
        )

    def remove_resource_skill(self, skill_id: str, *, expected_version: int) -> ResourceSkill:
        return self._capability_command.remove_resource_skill(
            skill_id, expected_version=expected_version
        )

    def add_resource_certification(
        self,
        resource_id: str,
        certification_code: str,
        certification_name: str,
        issued_date: date | None = None,
        expiry_date: date | None = None,
        certificate_number: str = "",
        issuer: str = "",
        notes: str = "",
    ) -> ResourceCertification:
        return self._capability_command.add_resource_certification(
            resource_id,
            certification_code,
            certification_name,
            issued_date,
            expiry_date,
            certificate_number,
            issuer,
            notes,
        )

    def update_resource_certification(
        self,
        *,
        cert_id: str,
        expected_version: int,
        certification_code: str,
        certification_name: str,
        issued_date: date | None = None,
        expiry_date: date | None = None,
        certificate_number: str = "",
        issuer: str = "",
        notes: str = "",
    ) -> ResourceCertification:
        return self._capability_command.update_resource_certification(
            cert_id=cert_id,
            expected_version=expected_version,
            certification_code=certification_code,
            certification_name=certification_name,
            issued_date=issued_date,
            expiry_date=expiry_date,
            certificate_number=certificate_number,
            issuer=issuer,
            notes=notes,
        )

    def remove_resource_certification(
        self, cert_id: str, *, expected_version: int
    ) -> ResourceCertification:
        return self._capability_command.remove_resource_certification(
            cert_id, expected_version=expected_version
        )

    def create_resource(
        self,
        name: str,
        role: str = "",
        *,
        code: str = "",
        kind: ResourceKind | str = ResourceKind.PERSON,
        hourly_rate: Decimal | int | str = Decimal(0),
        cost_type: CostType = CostType.LABOR,
        currency_code: str | None = None,
        capacity_percent: float = 100.0,
        is_active: bool = True,
        address: str = "",
        contact: str = "",
        worker_type: WorkerType | str = WorkerType.EXTERNAL,
        employee_id: str | None = None,
        department_id: str | None = None,
        site_id: str | None = None,
    ) -> Resource:
        return self._master_command.create_resource(
            name,
            role,
            code=code,
            kind=kind,
            hourly_rate=hourly_rate,
            cost_type=cost_type,
            currency_code=currency_code,
            capacity_percent=capacity_percent,
            is_active=is_active,
            address=address,
            contact=contact,
            worker_type=worker_type,
            employee_id=employee_id,
            department_id=department_id,
            site_id=site_id,
        )

    def update_resource(
        self,
        *,
        resource_id: str,
        expected_version: int,
        name: str,
        code: str,
        kind: ResourceKind | str,
        role: str,
        hourly_rate: Decimal | int | str,
        cost_type: CostType,
        currency_code: str | None,
        capacity_percent: float,
        address: str,
        contact: str,
        worker_type: WorkerType | str,
        employee_id: str | None,
        department_id: str | None,
        site_id: str | None,
    ) -> Resource:
        return self._master_command.update_resource(
            resource_id=resource_id,
            expected_version=expected_version,
            name=name,
            code=code,
            kind=kind,
            role=role,
            hourly_rate=hourly_rate,
            cost_type=cost_type,
            currency_code=currency_code,
            capacity_percent=capacity_percent,
            address=address,
            contact=contact,
            worker_type=worker_type,
            employee_id=employee_id,
            department_id=department_id,
            site_id=site_id,
        )

    def deactivate_resource(self, *, resource_id: str, expected_version: int) -> Resource:
        return self._master_command.deactivate_resource(
            resource_id=resource_id, expected_version=expected_version
        )

    def reactivate_resource(self, *, resource_id: str, expected_version: int) -> Resource:
        return self._master_command.reactivate_resource(
            resource_id=resource_id, expected_version=expected_version
        )

    def purge_resource(self, *, resource_id: str, expected_version: int) -> Resource:
        return self._master_command.purge_resource(
            resource_id=resource_id, expected_version=expected_version
        )

    def query_resource_projects_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        active: bool | None = None,
        status: ProjectStatus | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "projectName",
        sort_direction: str = "asc",
    ) -> ResourceProjectReadPage:
        return self._context_query.query_resource_projects_page(
            resource_id,
            search_text=search_text,
            active=active,
            status=status,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def query_resource_assignments_page(
        self,
        resource_id: str,
        *,
        search_text: str = "",
        project_id: str | None = None,
        task_status: TaskStatus | None = None,
        assignment_status: str | None = None,
        lifecycle: str = "current",
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "scheduledStart",
        sort_direction: str = "asc",
    ) -> ResourceAssignmentReadPage:
        return self._context_query.query_resource_assignments_page(
            resource_id,
            search_text=search_text,
            project_id=project_id,
            task_status=task_status,
            assignment_status=assignment_status,
            lifecycle=lifecycle,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
            sort_key=sort_key,
            sort_direction=sort_direction,
        )

    def query_resource_activity_page(
        self,
        resource_id: str,
        *,
        category: str = "all",
        start_date: date | None = None,
        end_date: date | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> ResourceActivityReadPage:
        return self._context_query.query_resource_activity_page(
            resource_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )


__all__ = ["ResourceService"]
