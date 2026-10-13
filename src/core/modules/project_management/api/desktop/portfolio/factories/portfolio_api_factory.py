"""Factory for building the portfolio desktop API."""

from src.core.modules.project_management.api.desktop.portfolio.api import (
    ProjectManagementPortfolioDesktopApi,
)
from src.core.modules.project_management.application.portfolio import PortfolioService
from src.core.modules.project_management.application.portfolio.queries.portfolio_intake import (
    PortfolioIntakeQueryHandler,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    PortfolioResourcePoolService,
)


def build_project_management_portfolio_desktop_api(
    *,
    project_service: ProjectService | None = None,
    portfolio_service: PortfolioService | None = None,
    portfolio_intake_query: PortfolioIntakeQueryHandler | None = None,
    pool_service: PortfolioResourcePoolService | None = None,
) -> ProjectManagementPortfolioDesktopApi:
    return ProjectManagementPortfolioDesktopApi(
        project_service=project_service,
        portfolio_service=portfolio_service,
        portfolio_intake_query=portfolio_intake_query,
        pool_service=pool_service,
    )


__all__ = ["build_project_management_portfolio_desktop_api"]
