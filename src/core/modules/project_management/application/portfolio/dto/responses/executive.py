from dataclasses import dataclass

from src.core.modules.project_management.domain.portfolio import (
    PortfolioExecutiveRow,
    PortfolioProjectDependencyView,
)


@dataclass(frozen=True, slots=True)
class PortfolioExecutiveSnapshot:
    heatmap: tuple[PortfolioExecutiveRow, ...] = ()
    dependencies: tuple[PortfolioProjectDependencyView, ...] = ()
    top_at_risk_projects: tuple[PortfolioExecutiveRow, ...] = ()
    hot_project_count: int = 0
    dependency_count: int = 0
