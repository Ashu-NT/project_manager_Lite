from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.invoicing.dto.responses.billing import (
    FinancialBillingPreparationResponse,
)
from src.core.modules.project_management.application.financials.invoicing.mappers.billing import (
    map_billing_preparation,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.billing_preparation import (
    ProjectBillingExternalEvent,
    ProjectBillingPreparation,
    ProjectBillingPreparationLine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class ProjectBillingPreparationQueryHandler(ProjectManagementModuleGuardMixin):
    """Read preparation evidence and authorized Accounting outcomes."""

    def __init__(self, *, billing_repo: ProjectBillingRepository, user_session=None, module_catalog_service=None) -> None:
        self._billing_repo = billing_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_preparation(self, preparation_id: str) -> FinancialBillingPreparationResponse:
        preparation = self._require_preparation(preparation_id)
        self._require(preparation.project_id, "finance.read", "view billing preparation")
        return map_billing_preparation(preparation)

    def list_preparations(
        self, project_id: str, *, offset: int = 0, limit: int = 50
    ) -> tuple[list[ProjectBillingPreparation], int]:
        self._require(project_id, "finance.read", "list billing preparations")
        return self._billing_repo.list_preparations(
            project_id, offset=offset, limit=limit
        )

    def list_latest_external_events(
        self, project_id: str, preparation_ids: tuple[str, ...]
    ) -> dict[str, ProjectBillingExternalEvent]:
        self._require(project_id, "finance.accounting_status.read", "list latest accounting outcomes")
        return self._billing_repo.list_latest_external_events(preparation_ids)

    def list_lines(self, preparation_id: str) -> list[ProjectBillingPreparationLine]:
        preparation = self.get_preparation(preparation_id)
        return self._billing_repo.list_preparation_lines(preparation.id)

    def list_external_events(self, preparation_id: str) -> list[ProjectBillingExternalEvent]:
        preparation = self.get_preparation(preparation_id)
        self._require(preparation.project_id, "finance.accounting_status.read", "view Accounting outcomes")
        return self._billing_repo.list_external_events(preparation.id)

    def _require_preparation(self, preparation_id: str) -> ProjectBillingPreparation:
        preparation = self._billing_repo.get_preparation(preparation_id)
        if preparation is None:
            raise NotFoundError(
                "Billing preparation not found.", code="BILLING_PREPARATION_NOT_FOUND"
            )
        return preparation

    def _require(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )

__all__ = ["ProjectBillingPreparationQueryHandler"]
