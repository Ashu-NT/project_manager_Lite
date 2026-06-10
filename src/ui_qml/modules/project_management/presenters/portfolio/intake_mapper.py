from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_intake_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.id,
        title=item.title,
        status_label=item.status_label,
        subtitle=str(item.sponsor_name or ""),
        supporting_text=(
            f"Budget {item.requested_budget_label} | Capacity {item.requested_capacity_label} | "
            f"Template {item.scoring_template_name}"
        ),
        meta_text=item.summary or f"Composite score: {item.composite_score}",
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "intakeItemId": item.id,
            "status": item.status,
            "scoringTemplateId": item.scoring_template_id,
            "version": item.version,
        },
    )
