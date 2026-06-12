from src.core.modules.project_management.api.desktop.portfolio.models.dependencies import PortfolioDependencyDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.formatters.date_formatter import format_datetime
from src.core.modules.project_management.api.desktop.portfolio.utils.dependency_type_utils import dependency_type_label


def serialize_dependency(row) -> PortfolioDependencyDesktopDto:
    dependency_type = row.dependency_type
    return PortfolioDependencyDesktopDto(
        dependency_id=row.dependency_id,
        predecessor_project_id=row.predecessor_project_id,
        predecessor_project_name=row.predecessor_project_name,
        predecessor_project_status_label=str(row.predecessor_project_status or "").replace("_", " ").title(),
        successor_project_id=row.successor_project_id,
        successor_project_name=row.successor_project_name,
        successor_project_status_label=str(row.successor_project_status or "").replace("_", " ").title(),
        dependency_type=dependency_type.value,
        dependency_type_label=dependency_type_label(dependency_type),
        summary=row.summary or "",
        pressure_label=row.pressure_label or "Stable",
        created_at_label=format_datetime(row.created_at),
    )


__all__ = ["serialize_dependency"]
