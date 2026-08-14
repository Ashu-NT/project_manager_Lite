from dataclasses import dataclass

from src.core.modules.project_management.api.desktop.portfolio.models.dependencies import (
    PortfolioDependencyDesktopDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.heatmap import (
    PortfolioHeatmapDesktopDto,
)


@dataclass(frozen=True)
class PortfolioExecutiveDesktopSnapshot:
    """Portfolio-wide aggregates for the Executive tab. hot_project_count and
    dependency_count are computed from the complete authorized scope and are
    independent of any Heatmap/Dependencies page size -- see R3.3.6.
    top_at_risk_projects is the same bounded/top_n ranking as
    PortfolioService.list_top_at_risk_projects(), derived here from the same
    single full-scope heatmap computation rather than a second scan."""

    heatmap: tuple[PortfolioHeatmapDesktopDto, ...] = ()
    dependencies: tuple[PortfolioDependencyDesktopDto, ...] = ()
    top_at_risk_projects: tuple[PortfolioHeatmapDesktopDto, ...] = ()
    hot_project_count: int = 0
    dependency_count: int = 0


__all__ = ["PortfolioExecutiveDesktopSnapshot"]
