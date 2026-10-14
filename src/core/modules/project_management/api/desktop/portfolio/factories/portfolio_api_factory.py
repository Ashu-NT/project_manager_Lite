"""Factory for building the portfolio desktop API."""

from src.core.modules.project_management.api.desktop.portfolio.api import (
    ProjectManagementPortfolioDesktopApi,
)
from src.core.modules.project_management.application.portfolio.commands import (
    PortfolioDependencyCommandHandler,
    PortfolioIntakeCommandHandler,
    PortfolioScenarioCommandHandler,
    PortfolioTemplateCommandHandler,
)
from src.core.modules.project_management.application.portfolio.queries import (
    PortfolioDependencyQueryHandler,
    PortfolioExecutiveQueryHandler,
    PortfolioIntakeQueryHandler,
    PortfolioScenarioQueryHandler,
    PortfolioTemplateQueryHandler,
)
from src.core.modules.project_management.application.projects import ProjectService
from src.core.modules.project_management.application.resources import (
    PortfolioResourcePoolService,
)


def build_project_management_portfolio_desktop_api(
    *,
    project_service: ProjectService | None = None,
    portfolio_intake_query: PortfolioIntakeQueryHandler | None = None,
    portfolio_intake_commands: PortfolioIntakeCommandHandler | None = None,
    portfolio_template_query: PortfolioTemplateQueryHandler | None = None,
    portfolio_template_commands: PortfolioTemplateCommandHandler | None = None,
    portfolio_scenario_query: PortfolioScenarioQueryHandler | None = None,
    portfolio_scenario_commands: PortfolioScenarioCommandHandler | None = None,
    portfolio_dependency_query: PortfolioDependencyQueryHandler | None = None,
    portfolio_dependency_commands: PortfolioDependencyCommandHandler | None = None,
    portfolio_executive_query: PortfolioExecutiveQueryHandler | None = None,
    pool_service: PortfolioResourcePoolService | None = None,
) -> ProjectManagementPortfolioDesktopApi:
    return ProjectManagementPortfolioDesktopApi(
        project_service=project_service,
        portfolio_intake_query=portfolio_intake_query,
        portfolio_intake_commands=portfolio_intake_commands,
        portfolio_template_query=portfolio_template_query,
        portfolio_template_commands=portfolio_template_commands,
        portfolio_scenario_query=portfolio_scenario_query,
        portfolio_scenario_commands=portfolio_scenario_commands,
        portfolio_dependency_query=portfolio_dependency_query,
        portfolio_dependency_commands=portfolio_dependency_commands,
        portfolio_executive_query=portfolio_executive_query,
        pool_service=pool_service,
    )


__all__ = ["build_project_management_portfolio_desktop_api"]
