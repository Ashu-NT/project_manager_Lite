from __future__ import annotations

from collections.abc import Iterable

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    TaskDetailLinkedDocumentFact,
)
from src.core.platform.domain.master_data.documents import Document


class CollaborationDocumentQueryMixin:
    def list_comment_documents_for_ids(
        self, task_id: str, comment_ids: tuple[str, ...]
    ) -> dict[str, tuple[TaskDetailLinkedDocumentFact, ...]]:
        task = self._require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view linked task documents")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view linked task documents",
        )
        if self._document_integration_service is None or not comment_ids:
            return {}
        if len(comment_ids) > 100:
            raise ValidationError(
                "At most 100 comment document references can be read at once.",
                code="COLLABORATION_DOCUMENT_PAGE_TOO_LARGE",
            )
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view linked task documents"
        )
        return self._workspace_reader.read_task_comment_documents(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            task_id=task_id,
            comment_ids=comment_ids,
        )

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
