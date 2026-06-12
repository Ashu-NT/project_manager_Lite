from src.core.modules.project_management.api.desktop.portfolio.models.recent_actions import PortfolioRecentActionDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.formatters.date_formatter import format_datetime


def serialize_recent_action(row) -> PortfolioRecentActionDesktopDto:
    return PortfolioRecentActionDesktopDto(
        occurred_at_label=format_datetime(row.occurred_at),
        project_name=row.project_name,
        actor_username=row.actor_username,
        action_label=row.action_label,
        summary=row.summary,
    )


__all__ = ["serialize_recent_action"]
