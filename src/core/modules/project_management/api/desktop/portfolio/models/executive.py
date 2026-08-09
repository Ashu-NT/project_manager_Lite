from dataclasses import dataclass

from src.core.modules.project_management.api.desktop.portfolio.models.dependencies import (
    PortfolioDependencyDesktopDto,
)
from src.core.modules.project_management.api.desktop.portfolio.models.heatmap import (
    PortfolioHeatmapDesktopDto,
)


@dataclass(frozen=True)
class PortfolioExecutiveDesktopSnapshot:
    heatmap: tuple[PortfolioHeatmapDesktopDto, ...] = ()
    dependencies: tuple[PortfolioDependencyDesktopDto, ...] = ()


__all__ = ["PortfolioExecutiveDesktopSnapshot"]
