from __future__ import annotations

from core.platform.access.authorization import require_project_permission
from core.platform.auth.authorization import require_permission
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


__all__ = ["CollaborationDocumentMixin"]
