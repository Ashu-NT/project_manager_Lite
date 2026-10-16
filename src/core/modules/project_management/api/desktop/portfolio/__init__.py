"""Portfolio desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.portfolio.api import (
    ProjectManagementPortfolioDesktopApi,
)
from src.core.modules.project_management.api.desktop.portfolio.factories.portfolio_api_factory import (
    build_project_management_portfolio_desktop_api,
)
from src.core.modules.project_management.api.desktop.portfolio.models import (
    PortfolioDependencyDesktopDto,
    PortfolioExecutiveDesktopSnapshot,
    PortfolioHeatmapDesktopDto,
    PortfolioOptionDescriptor,
    PortfolioProjectOptionDescriptor,
    PortfolioRecentActionDesktopDto,
    PortfolioScenarioComparisonDesktopDto,
    PortfolioScenarioDesktopDto,
    PortfolioScenarioEvaluationDesktopDto,
)

__all__ = ['PortfolioDependencyDesktopDto', 'PortfolioExecutiveDesktopSnapshot', 'PortfolioHeatmapDesktopDto', 'PortfolioOptionDescriptor', 'PortfolioProjectOptionDescriptor', 'PortfolioRecentActionDesktopDto', 'PortfolioScenarioComparisonDesktopDto', 'PortfolioScenarioDesktopDto', 'PortfolioScenarioEvaluationDesktopDto', 'ProjectManagementPortfolioDesktopApi', 'build_project_management_portfolio_desktop_api']
