from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.collaboration.utils.visibility import (
    CollaborationVisibilityPolicy,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.reads.collaboration import (
    CollaborationWorkspaceReader,
)
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    TaskDetailLinkedDocumentFact,
    TaskDocumentOptionFact,
)
from src.core.platform.application.master_data.documents.document_access import (
    attachment_visibility,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.contract.port.master_data.documents.document_access_policy import (
    DocumentAccessPolicy,
)


class CollaborationDocumentQueryHandler(ProjectManagementModuleGuardMixin):
    """Bounded linked-document reads for task comments."""

    def __init__(
        self,
        *,
        workspace_reader: CollaborationWorkspaceReader,
        policy: CollaborationVisibilityPolicy,
        tenant_context_service,
        user_session=None,
        module_catalog_service=None,
        document_access_policy: DocumentAccessPolicy | None = None,
    ) -> None:
        self._workspace_reader = workspace_reader
        self._policy = policy
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service
        self._document_access_policy = document_access_policy

    def list_comment_documents_for_ids(
        self, task_id: str, comment_ids: tuple[str, ...]
    ) -> dict[str, tuple[TaskDetailLinkedDocumentFact, ...]]:
        task = self._policy.require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view linked task documents")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view linked task documents",
        )
        if self._document_access_policy is None or not comment_ids:
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
            visibility=attachment_visibility(self._document_access_policy.visibility()),
        )

    def search_available_documents(
        self, task_id: str, *, query: str = "", limit: int = 50
    ) -> tuple[TaskDocumentOptionFact, ...]:
        task = self._policy.require_task(task_id)
        require_permission(self._user_session, "collaboration.read", operation_label="view shared document library")
        require_project_permission(
            self._user_session,
            task.project_id,
            "collaboration.read",
            operation_label="view shared document library",
        )
        if self._document_access_policy is None:
            return ()
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view shared document library"
        )
        return self._workspace_reader.read_document_options(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            visibility=attachment_visibility(self._document_access_policy.visibility()),
            query=(query or "").strip()[:128],
            limit=max(1, min(limit, 100)),
        )


__all__ = ["CollaborationDocumentQueryHandler"]
