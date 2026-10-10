from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.projects.commands.create import (
    ProjectCreateHandler,
)
from src.core.modules.project_management.application.projects.commands.deletion import (
    ProjectDeletionHandler,
)
from src.core.modules.project_management.application.projects.commands.status import (
    ProjectStatusHandler,
)
from src.core.modules.project_management.application.projects.commands.update import (
    ProjectUpdateHandler,
)
from src.core.modules.project_management.application.projects.queries.project_query import (
    ProjectQueryHandler,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.persistence.reads.projects import (
    SqlAlchemyProjectCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.projects.project_unit_of_work import (
    SqlAlchemyProjectUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle
from src.infra.persistence.db.unit_of_work import SqlAlchemyUnitOfWorkFactoryBase


def build_project_service(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
    shared_uow_factory: SqlAlchemyUnitOfWorkFactoryBase,
) -> ProjectService:
    project_uow_factory = SqlAlchemyProjectUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    catalog_reader = SqlAlchemyProjectCatalogReader(session=session)
    query_handler = ProjectQueryHandler(
        project_repo=repositories.pm.project_repo,
        project_catalog_reader=catalog_reader,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    return ProjectService(
        query_handler=query_handler,
        module_catalog_service=platform_services.module_catalog_service,
        user_session=platform_services.user_session,
        status_handler=ProjectStatusHandler(
            project_repo=repositories.pm.project_repo,
            uow_factory=project_uow_factory,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
        ),
        deletion_handler=ProjectDeletionHandler(
            session=session,
            project_repo=repositories.pm.project_repo,
            task_repo=repositories.pm.task_repo,
            dependency_repo=repositories.pm.dependency_repo,
            assignment_repo=repositories.pm.assignment_repo,
            time_entry_repo=repositories.platform.time_entry_repo,
            shared_uow_factory=shared_uow_factory,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
            activity_service=platform_services.activity_service,
            enterprise_audit_service=platform_services.enterprise_audit_service,
        ),
        create_handler=ProjectCreateHandler(
            project_repo=repositories.pm.project_repo,
            project_catalog_reader=catalog_reader,
            uow_factory=project_uow_factory,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
            party_repo=repositories.platform.party_repo,
            department_repo=repositories.platform.department_repo,
        ),
        update_handler=ProjectUpdateHandler(
            project_repo=repositories.pm.project_repo,
            task_repo=repositories.pm.task_repo,
            project_catalog_reader=catalog_reader,
            uow_factory=project_uow_factory,
            tenant_context_service=platform_services.tenant_context_service,
            user_session=platform_services.user_session,
            party_repo=repositories.platform.party_repo,
            department_repo=repositories.platform.department_repo,
        ),
    )
