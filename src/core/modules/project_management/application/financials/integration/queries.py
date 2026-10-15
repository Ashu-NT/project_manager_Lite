from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.contracts.reads.financials.integration.models.integration_facts import (
    ApprovedTimePostingFailurePage,
    ApprovedTimePostingFailureQuery,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import ConfigurationError

if TYPE_CHECKING:
    from src.core.modules.project_management.contracts.reads.financials.integration.reader import (
        FinanceIntegrationReader,
    )
    from src.core.platform.application.tenant.tenancy.tenant_context import (
        TenantContextService,
    )
    from src.core.platform.domain.security.auth.session import UserSessionContext


class IntegrationWorkspaceQueries:
    # Host attributes supplied by ``ProjectFinanceWorkspaceQuery`` (declared for type checking only).
    _integration_reader: FinanceIntegrationReader | None
    _tenant_context_service: TenantContextService | None
    _user_session: UserSessionContext | None
    _has_project_permission: Callable[[str, str], bool]

    def list_approved_time_posting_failures(
        self,
        project_id: str,
        *,
        request: ApprovedTimePostingFailureQuery,
    ) -> ApprovedTimePostingFailurePage:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view approved-time posting failures",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view approved-time posting failures",
        )
        if self._integration_reader is None or self._tenant_context_service is None:
            raise ConfigurationError("Finance Integration Reader is not configured.")
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="view approved-time posting failures"
        )
        page = self._integration_reader.list_approved_time_failures(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            request=request,
        )
        if self._has_project_permission(project_id, "finance.read_sensitive"):
            return page
        return replace(
            page,
            items=tuple(
                replace(
                    item,
                    resource_id="",
                    failure_message=(
                        "Detailed integration evidence requires sensitive Finance access."
                    ),
                )
                for item in page.items
            ),
        )
