from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.persistence.reads.register import (
    SqlAlchemyRegisterCatalogReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.register.register_unit_of_work import (
    SqlAlchemyRegisterUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_register_service(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> RegisterService:
    uow_factory = SqlAlchemyRegisterUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    return RegisterService(
        session=session,
        project_repo=repositories.pm.project_repo,
        register_repo=repositories.pm.register_repo,
        user_session=platform_services.user_session,
        activity_service=platform_services.activity_service,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        register_catalog_reader=SqlAlchemyRegisterCatalogReader(session=session),
        uow_factory=uow_factory,
    )
