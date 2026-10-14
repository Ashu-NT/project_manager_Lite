"""portfolio composition dependencies."""
from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class PortfolioComposition:
    intake_query: PortfolioIntakeQueryHandler
    intake_commands: PortfolioIntakeCommandHandler
    template_query: PortfolioTemplateQueryHandler
    template_commands: PortfolioTemplateCommandHandler
    scenario_query: PortfolioScenarioQueryHandler
    scenario_commands: PortfolioScenarioCommandHandler
    dependency_query: PortfolioDependencyQueryHandler
    dependency_commands: PortfolioDependencyCommandHandler
    executive_query: PortfolioExecutiveQueryHandler
