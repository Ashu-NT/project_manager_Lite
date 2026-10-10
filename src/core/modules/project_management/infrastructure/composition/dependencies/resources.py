from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.resources import (
    ProjectResourceService,
    ResourceService,
)
from src.core.modules.project_management.application.resources.capacity.enterprise_resource_availability import (
    EnterpriseResourceAvailabilityService,
)
from src.core.modules.project_management.application.resources.capacity.resource_capacity_calculator import (
    ResourceCapacityCalculator,
)
from src.core.modules.project_management.application.resources.capacity.resource_workload_service import (
    ResourceWorkloadService,
)
from src.core.modules.project_management.application.resources.catalog.assignment_validation import (
    AssignmentSkillValidator,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceCatalogReader,
    SqlAlchemyResourceContextReader,
    SqlAlchemyResourceWorkloadDemandReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.resources.resource_unit_of_work import (
    SqlAlchemyResourceUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bootstrap import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkFactoryBase


def build_project_resource_service(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    shared_uow_factory: SqlAlchemyUnitOfWorkFactoryBase,
) -> ProjectResourceService:
    return ProjectResourceService(
        project_resource_repo=repositories.project_resource_repo,
        resource_repo=repositories.resource_repo,
        project_repo=repositories.project_repo,
        session=session,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        task_repo=repositories.task_repo,
        assignment_repo=repositories.assignment_repo,
        financial_profile_repo=repositories.project_financial_profile_repo,
        shared_uow_factory=shared_uow_factory,
    )


def build_resource_planning_foundation(
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
) -> tuple[AssignmentSkillValidator, EnterpriseResourceAvailabilityService]:
    return (
        AssignmentSkillValidator(
            skill_repo=repositories.resource_skill_repo,
            cert_repo=repositories.resource_cert_repo,
            requirement_repo=repositories.task_skill_req_repo,
        ),
        EnterpriseResourceAvailabilityService(
            resolver=platform_services.platform_calendar_resolver,
            resource_repo=repositories.resource_repo,
        ),
    )


def build_resource_planning_services(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    availability_service: EnterpriseResourceAvailabilityService,
) -> tuple[ResourceCapacityCalculator, ResourceWorkloadService]:
    return (
        ResourceCapacityCalculator(availability_service=availability_service),
        ResourceWorkloadService(
            resource_repo=repositories.resource_repo,
            demand_reader=SqlAlchemyResourceWorkloadDemandReader(session=session),
            availability_service=availability_service,
            user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
        ),
    )


def build_resource_service(
    session: Session,
    repositories: RepositoryBundle,
    platform_services: PlatformServiceBundle,
    *,
    clock: SystemClock,
) -> ResourceService:
    catalog_reader = SqlAlchemyResourceCatalogReader(session=session)
    context_reader = SqlAlchemyResourceContextReader(session=session)
    uow_factory = SqlAlchemyResourceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    return ResourceService(
        session,
        repositories.resource_repo,
        repositories.assignment_repo,
        repositories.project_resource_repo,
        repositories.time_entry_repo,
        repositories.employee_repo,
        skill_repo=repositories.resource_skill_repo,
        cert_repo=repositories.resource_cert_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        resource_catalog_reader=catalog_reader,
        resource_inspector_reader=catalog_reader,
        resource_summary_reader=catalog_reader,
        resource_projects_reader=context_reader,
        resource_assignments_reader=context_reader,
        resource_activity_reader=context_reader,
        resource_capability_reader=context_reader,
        department_service=platform_services.department_service,
        site_service=platform_services.site_service,
        uow_factory=uow_factory,
        clock=clock,
    )
