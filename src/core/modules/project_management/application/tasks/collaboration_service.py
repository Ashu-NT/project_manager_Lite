from __future__ import annotations

import os

from sqlalchemy.orm import Session

from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin
from src.core.modules.project_management.application.tasks.collaboration_principal import (
    CollaborationPrincipalMixin,
)
from src.core.modules.project_management.application.tasks.collaboration_support import (
    CollaborationSupportMixin,
)
from src.core.modules.project_management.application.tasks.commands.collaboration_comments import (
    CollaborationCommentCommandMixin,
)
from src.core.modules.project_management.application.tasks.commands.collaboration_presence import (
    CollaborationPresenceCommandMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_comments import (
    CollaborationCommentQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_documents import (
    CollaborationDocumentQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_inbox import (
    CollaborationInboxQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_notifications import (
    CollaborationNotificationQueryMixin,
)
from src.core.modules.project_management.application.tasks.queries.collaboration_presence import (
    CollaborationPresenceQueryMixin,
)
from src.core.modules.project_management.contracts.repositories.collaboration import (
    TaskCommentRepository,
    TaskPresenceRepository,
)
from src.core.modules.project_management.contracts.repositories.project import ProjectRepository
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.platform.access.contracts import ProjectMembershipRepository
from src.core.platform.audit.contracts import AuditLogRepository
from src.core.platform.auth.contracts import UserRepository
from src.core.platform.documents import DocumentIntegrationService


class CollaborationService(
    ProjectManagementModuleGuardMixin,
    CollaborationCommentCommandMixin,
    CollaborationCommentQueryMixin,
    CollaborationDocumentQueryMixin,
    CollaborationInboxQueryMixin,
    CollaborationNotificationQueryMixin,
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
        audit_repo: AuditLogRepository,
        project_membership_repo: ProjectMembershipRepository,
        document_integration_service: DocumentIntegrationService | None = None,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._session = session
        self._comment_repo = comment_repo
        self._presence_repo = presence_repo
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._user_repo = user_repo
        self._audit_repo = audit_repo
        self._project_membership_repo = project_membership_repo
        self._document_integration_service = document_integration_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._presence_ttl_seconds = max(int(os.getenv("PM_TASK_PRESENCE_TTL_SECONDS", "900") or 900), 60)


__all__ = ["CollaborationService"]
