from __future__ import annotations

from typing import Iterable

from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission
from core.platform.common.exceptions import ValidationError
from core.platform.documents import Document


class CollaborationDocumentMixin:
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
        normalized = list(
            dict.fromkeys(
                str(item).strip()
                for item in (linked_document_ids or [])
                if str(item).strip()
            )
        )
        if normalized and self._document_integration_service is None:
            raise ValidationError(
                "Shared document linking is not available in the current collaboration runtime.",
                code="COLLABORATION_DOCUMENT_LIBRARY_UNAVAILABLE",
            )
        return normalized

    def _link_existing_comment_documents(self, *, comment_id: str, document_ids: Iterable[str]) -> None:
        if self._document_integration_service is None:
            return
        for document_id in document_ids:
            self._document_integration_service.link_existing_document(
                required_permission="collaboration.manage",
                operation_label="link shared document to task collaboration",
                module_code="project_management",
                entity_type="task_comment",
                entity_id=comment_id,
                document_id=document_id,
                link_role="reference",
            )


__all__ = ["CollaborationDocumentMixin"]
