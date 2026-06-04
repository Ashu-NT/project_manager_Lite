"""Portfolio desktop API — modular enterprise package."""

from src.core.modules.project_management.api.desktop.portfolio.api import ProjectManagementPortfolioDesktopApi
from src.core.modules.project_management.api.desktop.portfolio.commands.create_dependency import PortfolioDependencyCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.commands.create_intake import PortfolioIntakeCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.commands.create_scenario import PortfolioScenarioCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.commands.create_template import PortfolioTemplateCreateCommand
from src.core.modules.project_management.api.desktop.portfolio.factories.portfolio_api_factory import build_project_management_portfolio_desktop_api
from src.core.modules.project_management.api.desktop.portfolio.models import (
    PortfolioCapacityResourceDto,
    PortfolioDependencyDesktopDto,
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
    "PortfolioDependencyCreateCommand",
    "PortfolioDependencyDesktopDto",
    "PortfolioHeatmapDesktopDto",
    "PortfolioIntakeCreateCommand",
    "PortfolioIntakeDesktopDto",
    "PortfolioOptionDescriptor",
    "PortfolioProjectOptionDescriptor",
    "PortfolioRecentActionDesktopDto",
    "PortfolioScenarioComparisonDesktopDto",
    "PortfolioScenarioCreateCommand",
    "PortfolioScenarioDesktopDto",
    "PortfolioScenarioEvaluationDesktopDto",
    "PortfolioTemplateCreateCommand",
    "PortfolioTemplateDesktopDto",
    "ProjectManagementPortfolioDesktopApi",
    "build_project_management_portfolio_desktop_api",
]
