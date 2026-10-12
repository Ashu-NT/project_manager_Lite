from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

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
from src.core.modules.project_management.application.resources.commands.project_resource_commands import (
    ProjectResourceCommandHandler,
)
from src.core.modules.project_management.application.resources.commands.resource_commands import (
    ResourceMasterCommandHandler,
)
from src.core.modules.project_management.application.resources.commands.skill_commands import (
    ResourceCapabilityCommandHandler,
)
from src.core.modules.project_management.application.resources.queries.project_resource_queries import (
    ProjectResourceQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.resource_context_queries import (
    ResourceContextQueryHandler,
)
from src.core.modules.project_management.application.resources.queries.skill_queries import (
    ResourceCapabilityQueryHandler,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.resources.bundle import (
    ResourceComposition,
)
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceCatalogReader,
    SqlAlchemyResourceContextReader,
    SqlAlchemyResourceWorkloadDemandReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.resources.resource_unit_of_work import (
    SqlAlchemyResourceUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkFactoryBase


def build_project_resource_service(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    shared_uow_factory: SqlAlchemyUnitOfWorkFactoryBase,
) -> ProjectResourceService:
    return ProjectResourceService(
        command_handler=ProjectResourceCommandHandler(
            project_resource_repo=repositories.pm.project_resource_repo,
            resource_repo=repositories.pm.resource_repo,
            project_repo=repositories.pm.project_repo,
            user_session=platform_services.user_session,
            activity_service=platform_services.activity_service,
            tenant_context_service=platform_services.tenant_context_service,
            task_repo=repositories.pm.task_repo,
            assignment_repo=repositories.pm.assignment_repo,
            financial_profile_repo=repositories.pm.project_financial_profile_repo,
            shared_uow_factory=shared_uow_factory,
        ),
        query_handler=ProjectResourceQueryHandler(
            project_resource_repo=repositories.pm.project_resource_repo,
            task_repo=repositories.pm.task_repo,
            assignment_repo=repositories.pm.assignment_repo,
            user_session=platform_services.user_session,
        ),
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
    )


def build_resource_planning_foundation(
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> tuple[AssignmentSkillValidator, EnterpriseResourceAvailabilityService]:
    return (
        AssignmentSkillValidator(
            skill_repo=repositories.pm.resource_skill_repo,
            cert_repo=repositories.pm.resource_cert_repo,
            requirement_repo=repositories.pm.task_skill_req_repo,
        ),
        EnterpriseResourceAvailabilityService(
            resolver=platform_services.platform_calendar_resolver,
            resource_repo=repositories.pm.resource_repo,
        ),
    )


def build_resource_planning_services(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    *,
    availability_service: EnterpriseResourceAvailabilityService,
) -> tuple[ResourceCapacityCalculator, ResourceWorkloadService]:
    return (
        ResourceCapacityCalculator(availability_service=availability_service),
        ResourceWorkloadService(
            resource_repo=repositories.pm.resource_repo,
            demand_reader=SqlAlchemyResourceWorkloadDemandReader(session=session),
            availability_service=availability_service,
            user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
        ),
    )


def build_resource_capabilities(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> ResourceComposition:
    catalog_reader = SqlAlchemyResourceCatalogReader(session=session)
    context_reader = SqlAlchemyResourceContextReader(session=session)
    uow_factory = SqlAlchemyResourceUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    context_query = ResourceContextQueryHandler(
        resource_projects_reader=context_reader,
        resource_assignments_reader=context_reader,
        resource_activity_reader=context_reader,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    capability_query = ResourceCapabilityQueryHandler(
        resource_capability_reader=context_reader,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    service = ResourceService(
        resource_repo=repositories.pm.resource_repo,
        master_command_handler=ResourceMasterCommandHandler(
            resource_repo=repositories.pm.resource_repo,
            employee_repo=repositories.platform.employee_repo,
            department_service=platform_services.department_service,
            site_service=platform_services.site_service,
            user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
            uow_factory=uow_factory,
        ),
        capability_command_handler=ResourceCapabilityCommandHandler(
            skill_repo=repositories.pm.resource_skill_repo,
            cert_repo=repositories.pm.resource_cert_repo,
            user_session=platform_services.user_session,
            tenant_context_service=platform_services.tenant_context_service,
            uow_factory=uow_factory,
        ),
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        resource_catalog_reader=catalog_reader,
        resource_inspector_reader=catalog_reader,
        resource_summary_reader=catalog_reader,
    )
    return ResourceComposition(
        service=service,
        capability_query=capability_query,
        context_query=context_query,
    )
