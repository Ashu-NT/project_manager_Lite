"""Map portfolio capacity results to neutral responses."""

from src.core.modules.project_management.application.portfolio.dto.responses.capacity import (
    PortfolioCapacityResourceDto,
)
from src.core.modules.project_management.application.resources.portfolio.queries.resource_pool import (
    PortfolioResourcePoolReport,
)


def map_capacity_pool(
    report: PortfolioResourcePoolReport,
) -> tuple[PortfolioCapacityResourceDto, ...]:
    sorted_pool = sorted(
        report.pool, key=lambda r: float(r.peak_load_percent or 0.0), reverse=True
    )
    return tuple(
        PortfolioCapacityResourceDto(
            resource_id=str(summary.resource_id or ""),
            resource_name=str(
                summary.resource_name or summary.resource_id or "Resource"
            ),
            peak_load_percent=float(summary.peak_load_percent or 0.0),
            average_load_percent=float(summary.average_load_percent or 0.0),
            overloaded=bool(summary.overloaded),
            demand_entries=tuple(
                str(d.project_name or d.project_id or "")
                for d in summary.demands
                if d.project_name or d.project_id
            ),
        )
        for summary in sorted_pool
    )
