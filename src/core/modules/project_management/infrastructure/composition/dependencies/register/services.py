from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.risk import RegisterService
from src.core.modules.project_management.application.risk.commands.register_lifecycle import (
    RegisterLifecycleHandler,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.register.bundle import (
    RegisterComposition,
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
) -> RegisterComposition:
    uow_factory = SqlAlchemyRegisterUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    lifecycle = RegisterLifecycleHandler(
        project_repo=repositories.pm.project_repo,
        register_repo=repositories.pm.register_repo,
        user_session=platform_services.user_session,
        tenant_context_service=platform_services.tenant_context_service,
        uow_factory=uow_factory,
        module_catalog_service=platform_services.module_catalog_service,
    )
    service = RegisterService(
        project_repo=repositories.pm.project_repo,
        register_repo=repositories.pm.register_repo,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        register_catalog_reader=SqlAlchemyRegisterCatalogReader(session=session),
    )
    return RegisterComposition(service=service, lifecycle=lifecycle)
