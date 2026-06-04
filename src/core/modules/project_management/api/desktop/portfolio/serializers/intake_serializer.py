from src.core.modules.project_management.api.desktop.portfolio.models.intake import PortfolioIntakeDesktopDto
from src.core.modules.project_management.api.desktop.portfolio.formatters.money_formatter import format_money
from src.core.modules.project_management.api.desktop.portfolio.formatters.percent_formatter import format_percent
from src.core.modules.project_management.api.desktop.portfolio.formatters.date_formatter import format_date


def serialize_intake_item(item) -> PortfolioIntakeDesktopDto:
    return PortfolioIntakeDesktopDto(
        id=item.id,
        title=item.title,
        sponsor_name=item.sponsor_name,
        summary=item.summary or "",
        requested_budget=float(item.requested_budget or 0.0),
        requested_budget_label=format_money(item.requested_budget),
        requested_capacity_percent=float(item.requested_capacity_percent or 0.0),
        requested_capacity_label=format_percent(item.requested_capacity_percent),
        target_start_date=item.target_start_date,
        target_start_date_label=format_date(item.target_start_date),
        status=item.status.value,
        status_label=item.status.value.replace("_", " ").title(),
        scoring_template_id=item.scoring_template_id or "",
        scoring_template_name=item.scoring_template_name or "",
        composite_score=int(item.composite_score or 0),
        version=int(item.version or 1),
    )


__all__ = ["serialize_intake_item"]
