from __future__ import annotations

from src.src.core.modules.project_management.domain.portfolio import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
)
from src.core.platform.auth.authorization import require_permission


class PortfolioIntakeQueryMixin:
    def list_intake_items(
        self,
        *,
        status: PortfolioIntakeStatus | None = None,
    ) -> list[PortfolioIntakeItem]:
        require_permission(self._user_session, "portfolio.read", operation_label="view portfolio intake")
        rows = self._intake_repo.list_all()
        if status is None:
            return rows
        return [row for row in rows if row.status == status]


__all__ = ["PortfolioIntakeQueryMixin"]


