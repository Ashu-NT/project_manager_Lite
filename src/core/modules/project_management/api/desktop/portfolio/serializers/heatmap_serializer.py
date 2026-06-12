from src.core.modules.project_management.api.desktop.portfolio.models.heatmap import PortfolioHeatmapDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.formatters.money_formatter import format_signed_money
from src.core.modules.project_management.api.desktop.portfolio.formatters.percent_formatter import format_percent


def serialize_heatmap_row(row) -> PortfolioHeatmapDesktopDto:
    return PortfolioHeatmapDesktopDto(
        project_id=row.project_id,
        project_name=row.project_name,
        project_status_label=str(row.project_status or "").replace("_", " ").title(),
        late_tasks=int(row.late_tasks or 0),
        critical_tasks=int(row.critical_tasks or 0),
        peak_utilization_percent=float(row.peak_utilization_percent or 0.0),
        peak_utilization_label=format_percent(row.peak_utilization_percent),
        cost_variance=float(row.cost_variance or 0.0),
        cost_variance_label=format_signed_money(row.cost_variance),
        pressure_label=row.pressure_label or "Stable",
    )


__all__ = ["serialize_heatmap_row"]
