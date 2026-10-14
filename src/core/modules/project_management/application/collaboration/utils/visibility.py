"""Shared collaboration visibility + principal policy.

One explicit collaborator injected into every collaboration handler: it owns
the current-principal identity rules (user id, mention aliases, unread state),
task/project access checks, the tenant-scoped accessible-project set, and the
bounded mention-candidate directory lookups.
"""

from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    filter_project_rows,
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.collaboration import (
    CollaborationWorkspaceReader,
)
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    CollaborationCommentFact,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    TaskRepository,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
    TaskComment,
)
from src.core.modules.project_management.domain.collaboration.mentions.mention import (
    BROADCAST_MENTION_TOKENS,
    extract_mention_tokens,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.platform.common.ids import generate_id
from src.core.shared.events.domain_event_context import DomainEventContext


def new_collaboration_context() -> DomainEventContext:
    return DomainEventContext(correlation_id=generate_id(), causation_id=None)


class CollaborationVisibilityPolicy:
    def __init__(
        self,
        *,
        task_repo: TaskRepository,
        project_repo: ProjectRepository,
        workspace_reader: CollaborationWorkspaceReader,
        tenant_context_service=None,
        user_session=None,
    ) -> None:
        self._task_repo = task_repo
        self._project_repo = project_repo
        self._workspace_reader = workspace_reader
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session

    # -- principal ---------------------------------------------------------

    @property
    def principal(self):
        return self._user_session.principal if self._user_session is not None else None

    def principal_user_id(self) -> str:
        return str(getattr(self.principal, "user_id", "") or "").strip()

    def principal_aliases(self) -> set[str]:
        principal = self.principal
        if principal is None:
            return set()
        aliases: set[str] = set()
        if principal.username:
            aliases.add(principal.username.strip().lower())
        display_name = (principal.display_name or "").strip().lower()
        if display_name:
            aliases.add(display_name.strip(" @"))
            aliases.add(display_name.replace(" ", "").strip(" @"))
            aliases.add(display_name.replace(" ", ".").strip(" @"))
        return {alias for alias in aliases if alias}

    def principal_primary_alias(self) -> str:
        principal = self.principal
        if principal is None or not getattr(principal, "username", None):
            return ""
        return str(principal.username).strip().lower()

    def comment_mentions_principal(
        self,
        comment: TaskComment | CollaborationCommentFact,
    ) -> bool:
        if comment.is_deleted:
            return False
        principal_user_id = self.principal_user_id()
        mentioned_user_ids = {
            str(item).strip()
            for item in comment.mentioned_user_ids
            if str(item).strip()
        }
        if principal_user_id and principal_user_id in mentioned_user_ids:
            return True
        mentions = {item.lower() for item in comment.mentions}
        aliases = self.principal_aliases()
        return bool(aliases and not mentions.isdisjoint(aliases))

    def comment_is_unread_for_principal(
        self,
        comment: TaskComment | CollaborationCommentFact,
    ) -> bool:
        if not self.comment_mentions_principal(comment):
            return False
        principal_user_id = self.principal_user_id()
        if principal_user_id:
            read_by_user_ids = {
                str(item).strip()
                for item in comment.read_by_user_ids
                if str(item).strip()
            }
            if principal_user_id in read_by_user_ids:
                return False
        aliases = self.principal_aliases()
        read_by = {item.lower() for item in comment.read_by}
        return read_by.isdisjoint(aliases)

    # -- scope / access ----------------------------------------------------

    def require_active_scope(self, *, operation_label: str):
        if self._tenant_context_service is None:
            raise BusinessRuleError(
                "Active tenant context is required to view collaboration workspace.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        return self._tenant_context_service.require_active_scope_ids(
            operation_label=operation_label
        )

    def collaboration_scope(self, *, operation_label: str):
        scope = self.require_active_scope(operation_label=operation_label)
        projects = filter_project_rows(
            self._project_repo.list(),
            self._user_session,
            permission_code="collaboration.read",
            project_id_getter=lambda project: project.id,
        )
        return scope, {project.id: project.name for project in projects}

    def require_task(self, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        return task

    def require_task_access(self, task_id: str, permission_code: str, *, operation_label: str):
        """Resolve the task, then enforce the global and project-scoped grant."""
        task = self.require_task(task_id)
        require_permission(self._user_session, permission_code, operation_label=operation_label)
        require_project_permission(
            self._user_session,
            task.project_id,
            permission_code,
            operation_label=operation_label,
        )
        return task

    def project_name(self, project_id: str) -> str:
        project = self._project_repo.get(project_id)
        return project.name if project is not None else ""

    # -- mention directory -------------------------------------------------

    def mention_candidates_for_project(
        self,
        project_id: str,
        *,
        query: str = "",
        handles: tuple[str, ...] = (),
        limit: int | None = 50,
    ) -> list[CollaborationMentionCandidate]:
        scope = self.require_active_scope(
            operation_label="resolve collaboration mention candidates"
        )
        normalized_handles = tuple(dict.fromkeys(handle.lower() for handle in handles))
        if limit is not None:
            return list(
                self._workspace_reader.read_mention_candidates(
                    tenant_id=scope.tenant_id,
                    organization_id=scope.organization_id,
                    project_id=project_id,
                    query=query.strip()[:128],
                    handles=normalized_handles,
                    limit=limit,
                )
            )
        candidates: list[CollaborationMentionCandidate] = []
        while True:
            batch = self._workspace_reader.read_mention_candidates(
                tenant_id=scope.tenant_id,
                organization_id=scope.organization_id,
                project_id=project_id,
                handles=normalized_handles,
                offset=len(candidates),
                limit=500,
            )
            candidates.extend(batch)
            if len(batch) < 500:
                return candidates

    def mention_candidates_for_text(
        self, project_id: str, text: str
    ) -> list[CollaborationMentionCandidate]:
        tokens = tuple(dict.fromkeys(extract_mention_tokens(text)))
        if any(token in BROADCAST_MENTION_TOKENS for token in tokens):
            return self.mention_candidates_for_project(project_id, limit=None)
        handles = tuple(token for token in tokens if token not in BROADCAST_MENTION_TOKENS)
        candidates: list[CollaborationMentionCandidate] = []
        for start in range(0, len(handles), 500):
            candidates.extend(
                self.mention_candidates_for_project(
                    project_id, handles=handles[start : start + 500], limit=500
                )
            )
        return candidates


__all__ = ["CollaborationVisibilityPolicy", "new_collaboration_context"]
