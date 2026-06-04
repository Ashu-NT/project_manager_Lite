"""Factory for building the portfolio desktop API."""

from src.core.modules.project_management.api.desktop.portfolio.api import ProjectManagementPortfolioDesktopApi


def build_project_management_portfolio_desktop_api(
    *,
    project_service=None,
    portfolio_service=None,
    pool_service=None,
) -> ProjectManagementPortfolioDesktopApi:
    return ProjectManagementPortfolioDesktopApi(
        project_service=project_service,
        portfolio_service=portfolio_service,
        pool_service=pool_service,
    )


__all__ = ["build_project_management_portfolio_desktop_api"]
