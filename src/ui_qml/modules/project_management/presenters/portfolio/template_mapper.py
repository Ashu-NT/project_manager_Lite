from __future__ import annotations

from src.core.modules.project_management.application.portfolio.dto.responses.templates import (
    PortfolioTemplateResponseDto,
)
from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def template_weight_summary(item: PortfolioTemplateResponseDto) -> str:
    return (
        f"Strategic x{item.strategic_weight}, Value x{item.value_weight}, "
        f"Urgency x{item.urgency_weight}, Risk x{item.risk_weight}"
    )


def to_template_record(item: PortfolioTemplateResponseDto) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Active" if item.is_active else "Available",
        subtitle=template_weight_summary(item),
        supporting_text=item.summary or "No template summary recorded.",
        meta_text=(
            "This template currently drives composite intake scoring."
            if item.is_active
            else "Activate this template to make it the portfolio scoring baseline."
        ),
        can_primary_action=not item.is_active,
        can_secondary_action=False,
        state={"templateId": item.id, "isActive": item.is_active},
    )
