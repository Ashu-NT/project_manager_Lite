from __future__ import annotations

import os

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.collaboration.utils.principal import (
    CollaborationPrincipalMixin,
)
from src.core.modules.project_management.application.collaboration.utils.support import (
    CollaborationSupportMixin,
)
from src.core.modules.project_management.application.collaboration.commands.collaboration_comments import (
    CollaborationCommentCommandMixin,
)
from src.core.modules.project_management.application.collaboration.commands.collaboration_presence import (
    CollaborationPresenceCommandMixin,
)
from src.core.modules.project_management.application.collaboration.queries.collaboration_comments import (
    CollaborationCommentQueryMixin,
)
from src.core.modules.project_management.application.collaboration.queries.collaboration_documents import (
    CollaborationDocumentQueryMixin,
)
from src.core.modules.project_management.application.collaboration.queries.collaboration_inbox import (
    CollaborationInboxQueryMixin,
)
from src.core.modules.project_management.application.collaboration.queries.collaboration_presence import (
    CollaborationPresenceQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.collaboration.collaboration import (
    TaskCommentRepository,
    TaskPresenceRepository,
)
from src.core.modules.project_management.contracts.reads.collaboration import (
    CollaborationWorkspaceReader,
)
from src.core.modules.project_management.contracts.repositories.projects.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.tasks.task import TaskRepository
from src.core.platform.contract.repositories.security.auth import UserRepository
from src.core.platform.application.master_data.documents import DocumentIntegrationService


class CollaborationService(
    ProjectManagementModuleGuardMixin,
    CollaborationCommentCommandMixin,
    CollaborationCommentQueryMixin,
    CollaborationDocumentQueryMixin,
    CollaborationInboxQueryMixin,
    CollaborationPresenceCommandMixin,
    CollaborationPresenceQueryMixin,
    CollaborationPrincipalMixin,
    CollaborationSupportMixin,
):
    def __init__(
        self,
        *,
        session: Session,
        comment_repo: TaskCommentRepository,
        presence_repo: TaskPresenceRepository,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        user_repo: UserRepository,
        workspace_reader: CollaborationWorkspaceReader,
        document_integration_service: DocumentIntegrationService | None = None,
        user_session=None,
        module_catalog_service=None,
        tenant_context_service=None,
        role_repo=None,
        role_binding_repo=None,
        notification_service=None,
        view_invalidation_channel=None,
    ) -> None:
        self._session = session
        self._comment_repo = comment_repo
        self._presence_repo = presence_repo
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._user_repo = user_repo
        self._workspace_reader = workspace_reader
        self._document_integration_service = document_integration_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._tenant_context_service = tenant_context_service
        self._role_repo = role_repo
        self._role_binding_repo = role_binding_repo
        self._notification_service = notification_service
        self._view_invalidation_channel = view_invalidation_channel
        self._presence_ttl_seconds = max(int(os.getenv("PM_TASK_PRESENCE_TTL_SECONDS", "900") or 900), 60)


__all__ = ["CollaborationService"]
