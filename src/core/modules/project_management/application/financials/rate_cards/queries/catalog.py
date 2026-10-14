from __future__ import annotations

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_cards import (
    ProjectRateCardRepository,
)
from src.core.modules.project_management.domain.financials.rate_cards import (
    ProjectRateCard,
    RateCardLine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class ProjectRateCardQueryHandler(ProjectManagementModuleGuardMixin):
    """Authorized rate-card and sensitive rate-line catalog reads."""

    def __init__(
        self,
        *,
        rate_card_repo: ProjectRateCardRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._rate_card_repo = rate_card_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def list_rate_cards(
        self,
        *,
        project_id: str | None = None,
        include_inactive: bool = False,
    ) -> list[ProjectRateCard]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list rate cards",
        )
        return self._rate_card_repo.list(project_id=project_id, include_inactive=include_inactive)

    def list_lines(
        self,
        rate_card_id: str,
        *,
        include_inactive: bool = False,
    ) -> list[RateCardLine]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list rate card lines",
        )
        require_permission(
            self._user_session,
            "finance.read_sensitive",
            operation_label="list sensitive rate card lines",
        )
        return self._rate_card_repo.list_lines(rate_card_id, include_inactive=include_inactive)


__all__ = ["ProjectRateCardQueryHandler"]
