"""Portfolio desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.portfolio.api import (
    ProjectManagementPortfolioDesktopApi,
)
from src.core.modules.project_management.api.desktop.portfolio.factories.portfolio_api_factory import (
    build_project_management_portfolio_desktop_api,
)
from src.core.modules.project_management.api.desktop.portfolio.models import (
    PortfolioCapacityResourceDto,
    PortfolioDependencyDesktopDto,
    PortfolioExecutiveDesktopSnapshot,
    PortfolioHeatmapDesktopDto,
    PortfolioIntakeDesktopDto,
    PortfolioOptionDescriptor,
    PortfolioProjectOptionDescriptor,
    PortfolioRecentActionDesktopDto,
    PortfolioScenarioComparisonDesktopDto,
    PortfolioScenarioDesktopDto,
    PortfolioScenarioEvaluationDesktopDto,
    PortfolioTemplateDesktopDto,
)

__all__ = [
    "PortfolioCapacityResourceDto",
    "PortfolioDependencyDesktopDto",
    "PortfolioExecutiveDesktopSnapshot",
    "PortfolioHeatmapDesktopDto",
    "PortfolioIntakeDesktopDto",
    "PortfolioOptionDescriptor",
    "PortfolioProjectOptionDescriptor",
    "PortfolioRecentActionDesktopDto",
    "PortfolioScenarioComparisonDesktopDto",
    "PortfolioScenarioDesktopDto",
    "PortfolioScenarioEvaluationDesktopDto",
    "PortfolioTemplateDesktopDto",
    "ProjectManagementPortfolioDesktopApi",
    "build_project_management_portfolio_desktop_api",
]
