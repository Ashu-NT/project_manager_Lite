from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.portfolio import (
    PortfolioRecordViewModel,
)


def to_template_record(item) -> PortfolioRecordViewModel:
    return PortfolioRecordViewModel(
        id=item.id,
        title=item.name,
        status_label="Active" if item.is_active else "Available",
        subtitle=item.weight_summary,
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
