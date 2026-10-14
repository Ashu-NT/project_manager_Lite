from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.financials.financial_changes.policy import (
    FinancialChangeAccessPolicy,
)
from src.core.modules.project_management.contracts.repositories.finance.financial_changes.financial_change import (
    FinancialChangeRepository,
)
from src.core.modules.project_management.domain.financials.financial_change import (
    FinancialChangeImpact,
    FinancialChangeRequest,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class FinancialChangeQueryHandler(FinancialChangeAccessPolicy):
    """Authorized domain reads, separate from workspace projection queries."""

    def __init__(
        self,
        *,
        change_repo: FinancialChangeRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._change_repo = change_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_change(self, change_id: str) -> FinancialChangeRequest:
        require_permission(
            self._user_session, "finance.read", operation_label="view financial change"
        )
        change = self._require_change(change_id)
        require_project_permission(
            self._user_session,
            change.project_id,
            "finance.read",
            operation_label="view financial change",
        )
        return change

    def list_changes(self, project_id: str) -> list[FinancialChangeRequest]:
        self._require_project_permission(
            project_id, "finance.read", "list financial changes"
        )
        return self._change_repo.list_for_project(project_id)

    def list_impacts(self, change_id: str) -> list[FinancialChangeImpact]:
        change = self.get_change(change_id)
        return self._change_repo.list_impacts(change.id)


__all__ = ["FinancialChangeQueryHandler"]
