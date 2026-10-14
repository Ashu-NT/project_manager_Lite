from __future__ import annotations

from src.core.platform.application.tenant.tenancy import TenantContextService
from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.contract.repositories.approval.contracts import (
    ApprovalRepository,
)


class ApprovalScope:
    def __init__(self, tenant_context: TenantContextService | None = None) -> None:
        self.tenant_context = tenant_context

    def active_organization_id(self, *, operation_label: str) -> str | None:
        if self.tenant_context is None:
            return None
        return self.tenant_context.require_active_organization_id(operation_label=operation_label)

    def assert_project_in_active_organization(
        self,
        approval_repo: ApprovalRepository,
        project_id: str | None,
        *,
        operation_label: str,
    ) -> None:
        organization_id = self.active_organization_id(operation_label=operation_label)
        if not organization_id or not project_id:
            return
        if (
            hasattr(approval_repo, "project_in_different_organization")
            and approval_repo.project_in_different_organization(project_id, organization_id)
        ):
            raise NotFoundError("Approval request not found.", code="APPROVAL_NOT_FOUND")
