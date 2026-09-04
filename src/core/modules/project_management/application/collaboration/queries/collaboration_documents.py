from __future__ import annotations

from typing import Iterable

from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.master_data.documents import Document


class CollaborationDocumentQueryMixin:
    def list_comment_documents(self, task_id: str) -> dict[str, list[Document]]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view linked task documents")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view linked task documents",
        )
        comments = self._comment_repo.list_by_task(task_id)
        if self._document_integration_service is None or not comments:
            return {comment.id: [] for comment in comments}
        documents_by_comment: dict[str, list[Document]] = {}
        for comment in comments:
            documents_by_comment[comment.id] = self._document_integration_service.list_documents_for_entity(
                required_permission="collaboration.read",
                operation_label="view linked task documents",
                module_code="project_management",
                entity_type="task_comment",
                entity_id=comment.id,
                active_only=True,
            )
        return documents_by_comment

    def list_available_documents(self, *, active_only: bool | None = True) -> list[Document]:
        require_permission(self._user_session, "collaboration.read", operation_label="view shared document library")
        if self._document_integration_service is None:
            return []
        return self._document_integration_service.list_available_documents(
            required_permission="collaboration.read",
            operation_label="view shared document library",
            active_only=active_only,
        )

    def _normalize_linked_document_ids(self, linked_document_ids: Iterable[str] | None) -> list[str]:
        normalized = list(dict.fromkeys(str(item).strip() for item in (linked_document_ids or []) if str(item).strip()))
        if normalized and self._document_integration_service is None:
            raise ValidationError(
                "Shared document linking is not available in the current collaboration runtime.",
                code="COLLABORATION_DOCUMENT_LIBRARY_UNAVAILABLE",
            )
        return normalized

__all__ = ["CollaborationDocumentQueryMixin"]
