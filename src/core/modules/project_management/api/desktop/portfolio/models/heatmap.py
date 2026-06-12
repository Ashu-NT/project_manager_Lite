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
    cost_variance: float
    cost_variance_label: str
    pressure_label: str


__all__ = ["PortfolioHeatmapDesktopDto"]
