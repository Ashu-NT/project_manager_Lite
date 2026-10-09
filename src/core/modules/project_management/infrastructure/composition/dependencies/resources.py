from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.application.resources import ResourceService
from src.core.modules.project_management.infrastructure.persistence.reads.resources import (
    SqlAlchemyResourceCatalogReader,
    SqlAlchemyResourceContextReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.resources.resource_unit_of_work import (
    SqlAlchemyResourceUnitOfWorkFactory,
)
from src.infra.composition.modules.platform_registry import PlatformServiceBundle
from src.infra.composition.persistence.repositories import RepositoryBundle


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
