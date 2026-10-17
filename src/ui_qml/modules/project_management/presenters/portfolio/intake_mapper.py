from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.application.portfolio.dto.responses.intake import (
    PortfolioIntakeResponse,
)
from src.ui_qml.modules.project_management.presenters.portfolio.formatting import (
    format_percent,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_intake_record(item: PortfolioIntakeResponse) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.id,
        title=item.title,
        status_label=item.status.value.replace("_", " ").title(),
        subtitle=str(item.sponsor_name or ""),
        supporting_text=(
            f"Budget {format_money(item.requested_budget)} | Capacity {format_percent(item.requested_capacity_percent)} | "
            f"Template {item.scoring_template_name}"
        ),
        meta_text=item.summary or f"Composite score: {item.composite_score}",
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "intakeItemId": item.id,
            "status": item.status.value,
            "scoringTemplateId": item.scoring_template_id,
            "version": item.version,
        },
    )
