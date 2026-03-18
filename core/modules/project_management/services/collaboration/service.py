from __future__ import annotations

import os

from sqlalchemy.orm import Session

from core.platform.common.interfaces import (
    AuditLogRepository,
    ProjectMembershipRepository,
    ProjectRepository,
    TaskCommentRepository,
    TaskPresenceRepository,
    TaskRepository,
    UserRepository,
)
from core.modules.project_management.services.collaboration.comments import CollaborationCommentMixin
from core.modules.project_management.services.collaboration.inbox import CollaborationInboxMixin
from core.modules.project_management.services.collaboration.notifications import CollaborationNotificationMixin
from core.modules.project_management.services.collaboration.presence import CollaborationPresenceMixin
from core.modules.project_management.services.collaboration.principal import CollaborationPrincipalMixin
from core.modules.project_management.services.collaboration.support import CollaborationSupportMixin
from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin


class CollaborationService(
    ProjectManagementModuleGuardMixin,
    CollaborationCommentMixin,
    CollaborationInboxMixin,
    CollaborationNotificationMixin,
    CollaborationPresenceMixin,
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
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._presence_ttl_seconds = max(int(os.getenv("PM_TASK_PRESENCE_TTL_SECONDS", "900") or 900), 60)


__all__ = ["CollaborationService"]
