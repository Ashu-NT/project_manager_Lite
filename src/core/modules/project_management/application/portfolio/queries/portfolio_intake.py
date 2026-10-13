from __future__ import annotations

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.common.pagination import (
    PaginatedResult,
)
from src.core.modules.project_management.contracts.reads.sorting import (
    ReadSort,
    ReadSortDirection,
)
from src.core.modules.project_management.contracts.repositories.portfolio.portfolio import (
    PortfolioIntakeRepository,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.domain.security.auth.session import UserSessionContext

_INTAKE_BROWSE_SORT_KEYS = {"title", "sponsorName", "statusLabel", "targetStartDate", "updatedAt"}


class PortfolioIntakeQueryHandler(ProjectManagementModuleGuardMixin):
    def __init__(
        self,
        *,
        intake_repo: PortfolioIntakeRepository,
        tenant_context_service: TenantContextService,
        user_session: UserSessionContext | None = None,
        module_catalog_service=None,
    ) -> None:
        self._intake_repo = intake_repo
        self._tenant_context_service = tenant_context_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _require_organization(self) -> None:
        self._tenant_context_service.require_active_organization_id(
            operation_label="view portfolio intake"
        )

    def list_intake_items(
        self,
        *,
        status: PortfolioIntakeStatus | None = None,
    ) -> list[PortfolioIntakeItem]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio intake")
        self._require_organization()
        rows = self._intake_repo.list()
        if status is None:
            return rows
        return [row for row in rows if row.status == status]

    def list_intake_items_page(
        self,
        *,
        status: PortfolioIntakeStatus | None = None,
        search_text: str = "",
        page: int = 1,
        page_size: int = 25,
        sort_key: str = "updatedAt",
        sort_direction: str = "desc",
    ) -> PaginatedResult[PortfolioIntakeItem]:
        """Authoritative server-paginated Intake browse. Intake is classified
        SCALABLE (candidate/proposed projects accumulate without a natural
        ceiling) — scope/filter/sort/pagination all happen in SQL."""
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio intake")
        self._require_organization()
        sort = ReadSort.normalize(
            key=sort_key,
            direction=sort_direction,
            allowed_keys=_INTAKE_BROWSE_SORT_KEYS,
            default_key="updatedAt",
            default_direction=ReadSortDirection.DESCENDING,
        )
        return self._intake_repo.list_page(
            status=status,
            search_text=search_text,
            page=page,
            page_size=page_size,
            sort=sort,
        )


__all__ = ["PortfolioIntakeQueryHandler"]
