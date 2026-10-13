from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.collaboration import (
    CollaborationService,
)
from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.infrastructure.collaboration_attachments import (
    cleanup_task_comment_attachments,
    store_task_comment_attachments,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration import (
    SqlAlchemyCollaborationWorkspaceReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.collaboration.collaboration_unit_of_work import (
    SqlAlchemyCollaborationUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_collaboration_service(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> CollaborationService:
    uow_factory = SqlAlchemyCollaborationUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    return CollaborationService(
        session=session,
        comment_repo=repositories.pm.task_comment_repo,
        presence_repo=repositories.pm.task_presence_repo,
        task_repo=repositories.pm.task_repo,
        project_repo=repositories.pm.project_repo,
        user_repo=repositories.platform.user_repo,
        workspace_reader=SqlAlchemyCollaborationWorkspaceReader(session=session),
        document_integration_service=platform_services.document_integration_service,
        user_session=platform_services.user_session,
        module_catalog_service=platform_services.module_catalog_service,
        tenant_context_service=platform_services.tenant_context_service,
        role_repo=repositories.platform.role_repo,
        role_binding_repo=repositories.platform.role_binding_repo,
        view_invalidation_channel=platform_services.platform_view_invalidation_channel,
        uow_factory=uow_factory,
        attachment_store=store_task_comment_attachments,
        attachment_cleanup=cleanup_task_comment_attachments,
        clock=SystemClock(),
    )
