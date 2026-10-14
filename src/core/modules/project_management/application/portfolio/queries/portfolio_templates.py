from __future__ import annotations

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.portfolio.utils.portfolio_policy import (
    PortfolioPolicy,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioScoringTemplate,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class PortfolioTemplateQueryHandler(ProjectManagementModuleGuardMixin):
    """Scoring-template reads. Bootstraps the default template through the
    shared policy (its own UoW) when no active template exists yet."""

    def __init__(
        self,
        *,
        policy: PortfolioPolicy,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._policy = policy
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def list_scoring_templates(self) -> list[PortfolioScoringTemplate]:
        require_permission(self._user_session, "portfolio.read", operation_label="view scoring templates")
        return self._policy.scoring_templates_with_bootstrap()

    def get_active_scoring_template(self) -> PortfolioScoringTemplate:
        require_permission(self._user_session, "portfolio.read", operation_label="view active scoring template")
        return self._policy.active_scoring_template_resolved()


__all__ = ["PortfolioTemplateQueryHandler"]
