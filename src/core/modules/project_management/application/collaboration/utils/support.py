from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    filter_project_rows,
)
from src.core.modules.project_management.domain.collaboration import (
    CollaborationMentionCandidate,
)
from src.core.modules.project_management.domain.collaboration.mentions.mention import (
    BROADCAST_MENTION_TOKENS,
    extract_mention_tokens,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


class CollaborationSupportMixin:
    def _collaboration_scope(self, *, operation_label: str):
        tenant_context = getattr(self, "_tenant_context_service", None)
        if tenant_context is None:
            raise BusinessRuleError(
                "Active tenant context is required to view collaboration workspace.",
                code="TENANT_CONTEXT_REQUIRED",
            )
        scope = tenant_context.require_active_scope_ids(operation_label=operation_label)
        projects = filter_project_rows(
            self._project_repo.list(),
            self._user_session,
            permission_code="collaboration.read",
            project_id_getter=lambda project: project.id,
        )
        return scope, {project.id: project.name for project in projects}

    def _list_mention_candidates_for_project(
        self,
        project_id: str,
        *,
        query: str = "",
        handles: tuple[str, ...] = (),
        limit: int | None = 50,
    ) -> list[CollaborationMentionCandidate]:
        scope = self._tenant_context_service.require_active_scope_ids(
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

    def _mention_candidates_for_text(
        self, project_id: str, text: str
    ) -> list[CollaborationMentionCandidate]:
        tokens = tuple(dict.fromkeys(extract_mention_tokens(text)))
        if any(token in BROADCAST_MENTION_TOKENS for token in tokens):
            return self._list_mention_candidates_for_project(project_id, limit=None)
        handles = tuple(token for token in tokens if token not in BROADCAST_MENTION_TOKENS)
        candidates: list[CollaborationMentionCandidate] = []
        for start in range(0, len(handles), 500):
            candidates.extend(
                self._list_mention_candidates_for_project(
                    project_id, handles=handles[start : start + 500], limit=500
                )
            )
        return candidates

    def _require_task(self, task_id: str):
        task = self._task_repo.get(task_id)
        if task is None:
            raise NotFoundError("Task not found.", code="TASK_NOT_FOUND")
        return task

    @staticmethod
    def _body_preview(body: str) -> str:
        text = " ".join((body or "").split())
        return text if len(text) <= 120 else f"{text[:117]}..."


__all__ = ["CollaborationSupportMixin"]
