from __future__ import annotations

from src.core.modules.project_management.domain.portfolio import PortfolioScoringTemplate
from src.core.platform.auth.authorization import require_permission


class PortfolioTemplateQueryMixin:
    def list_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        require_permission(self._user_session, "portfolio.read", operation_label="view scoring templates")
        return self._ensure_scoring_templates()

    def get_active_scoring_template(self) -> PortfolioScoringTemplate:
        require_permission(self._user_session, "portfolio.read", operation_label="view active scoring template")
        return self._active_scoring_template()


__all__ = ["PortfolioTemplateQueryMixin"]
