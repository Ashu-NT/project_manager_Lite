from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioHeatmapDesktopDto:
    project_id: str
    project_name: str
    project_status_label: str
    late_tasks: int
    critical_tasks: int
    peak_utilization_percent: float
    peak_utilization_label: str
    cost_variance: str
    cost_variance_label: str
    pressure_label: str


@dataclass(frozen=True)
class PortfolioHeatmapPageDto:
    """Authoritative server-paginated Heatmap browse page. Pressure is
    display-only here (see PortfolioService.list_portfolio_heatmap_page) --
    sort_key can never be a pressure field."""

    items: tuple[PortfolioHeatmapDesktopDto, ...] = ()
    total: int = 0
    page: int = 1
    page_size: int = 25
    sort_key: str = "projectName"
    sort_direction: str = "asc"
    search_text: str = ""


__all__ = ["PortfolioHeatmapDesktopDto", "PortfolioHeatmapPageDto"]
