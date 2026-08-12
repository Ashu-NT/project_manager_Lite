"""Portfolio domain -- intake, scenarios, scoring templates, cross-project
dependencies, and executive/reporting row shapes. Split by content into
sibling modules (intake, scenario, scoring_template, dependency, reporting,
validation); re-exported here as the package's stable public surface."""

from src.core.modules.project_management.domain.portfolio.dependency import (
    PortfolioProjectDependency,
    PortfolioProjectDependencyView,
)
from src.core.modules.project_management.domain.portfolio.intake import (
    PortfolioIntakeItem,
    PortfolioIntakeStatus,
    as_portfolio_intake_status,
    calculate_portfolio_intake_composite_score,
)
from src.core.modules.project_management.domain.portfolio.reporting import (
    PortfolioExecutiveRow,
    PortfolioRecentAction,
)
from src.core.modules.project_management.domain.portfolio.scenario import (
    PortfolioScenario,
    PortfolioScenarioComparison,
    PortfolioScenarioEvaluation,
)
from src.core.modules.project_management.domain.portfolio.scoring_template import (
    PortfolioScoringTemplate,
)

__all__ = [
    "PortfolioIntakeStatus",
    "as_portfolio_intake_status",
    "calculate_portfolio_intake_composite_score",
    "PortfolioIntakeItem",
    "PortfolioScoringTemplate",
    "PortfolioExecutiveRow",
    "PortfolioRecentAction",
    "PortfolioScenario",
    "PortfolioScenarioEvaluation",
    "PortfolioScenarioComparison",
    "PortfolioProjectDependency",
    "PortfolioProjectDependencyView",
]
