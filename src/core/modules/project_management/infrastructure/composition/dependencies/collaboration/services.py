"""collaboration composition dependencies."""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from src.core.modules.project_management.application.collaboration.commands import (
    CollaborationCommentCommandHandler,
    CollaborationCommentEngagementHandler,
    CollaborationPresenceCommandHandler,
)
from src.core.modules.project_management.application.collaboration.queries import (
    CollaborationCommentQueryHandler,
    CollaborationDocumentQueryHandler,
    CollaborationInboxQueryHandler,
    CollaborationPresenceQueryHandler,
)
from src.core.modules.project_management.application.collaboration.utils.visibility import (
    CollaborationVisibilityPolicy,
)
from src.core.modules.project_management.application.common.clock import SystemClock
from src.core.modules.project_management.infrastructure.collaboration_attachments import (
    cleanup_task_comment_attachments,
    store_task_comment_attachments,
)
from src.core.modules.project_management.infrastructure.composition.context import (
    ProjectManagementRepositoryContext,
)
from src.core.modules.project_management.infrastructure.composition.dependencies.collaboration.bundle import (
    CollaborationComposition,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration import (
    SqlAlchemyCollaborationWorkspaceReader,
)
from src.core.modules.project_management.infrastructure.persistence.uow.collaboration.collaboration_unit_of_work import (
    SqlAlchemyCollaborationUnitOfWorkFactory,
)
from src.core.platform.infrastructure.composition.bundle import PlatformServiceBundle


def build_collaboration_capabilities(
    session: Session,
    repositories: ProjectManagementRepositoryContext,
    platform_services: PlatformServiceBundle,
) -> CollaborationComposition:
    uow_factory = SqlAlchemyCollaborationUnitOfWorkFactory(
        session_factory=sessionmaker(bind=platform_services.session.bind, future=True),
        transactional_dispatcher=platform_services.platform_transactional_dispatcher,
        post_commit_bus=platform_services.platform_post_commit_bus,
        tenant_context_service=platform_services.tenant_context_service,
        user_session=platform_services.user_session,
    )
    tenant_context_service = platform_services.tenant_context_service
    user_session = platform_services.user_session
    module_catalog_service = platform_services.module_catalog_service
    workspace_reader = SqlAlchemyCollaborationWorkspaceReader(session=session)
    policy = CollaborationVisibilityPolicy(
        task_repo=repositories.pm.task_repo,
        project_repo=repositories.pm.project_repo,
        workspace_reader=workspace_reader,
        tenant_context_service=tenant_context_service,
        user_session=user_session,
    )
    comment_writes: dict[str, Any] = {
        "comment_repo": repositories.pm.task_comment_repo,
        "policy": policy,
        "uow_factory": uow_factory,
        "tenant_context_service": tenant_context_service,
        "user_session": user_session,
        "module_catalog_service": module_catalog_service,
    }
    return CollaborationComposition(
        comment_commands=CollaborationCommentCommandHandler(
            **comment_writes,
            document_access_policy=platform_services.document_access_policy,
            attachment_store=store_task_comment_attachments,
            attachment_cleanup=cleanup_task_comment_attachments,
            clock=SystemClock(),
        ),
        comment_engagement=CollaborationCommentEngagementHandler(**comment_writes),
        presence_commands=CollaborationPresenceCommandHandler(
            policy=policy,
            uow_factory=uow_factory,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
            view_invalidation_channel=platform_services.platform_view_invalidation_channel,
        ),
        comment_query=CollaborationCommentQueryHandler(
            workspace_reader=workspace_reader,
            policy=policy,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
        ),
        document_query=CollaborationDocumentQueryHandler(
            workspace_reader=workspace_reader,
            policy=policy,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
            document_access_policy=platform_services.document_access_policy,
        ),
        inbox_query=CollaborationInboxQueryHandler(
            workspace_reader=workspace_reader,
            policy=policy,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
        ),
        presence_query=CollaborationPresenceQueryHandler(
            workspace_reader=workspace_reader,
            policy=policy,
            tenant_context_service=tenant_context_service,
            user_session=user_session,
            module_catalog_service=module_catalog_service,
            presence_repo=repositories.pm.task_presence_repo,
        ),
    )
