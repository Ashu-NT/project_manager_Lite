from __future__ import annotations

from src.core.modules.project_management.application.portfolio.dto.responses.intake import (
    PortfolioIntakeResponse,
)
from src.core.modules.project_management.domain.portfolio import PortfolioIntakeItem


def map_intake_response(item: PortfolioIntakeItem) -> PortfolioIntakeResponse:
    return PortfolioIntakeResponse(
        id=item.id,
        title=item.title,
        sponsor_name=item.sponsor_name,
        organization_id=item.organization_id,
        summary=item.summary,
        requested_budget=item.requested_budget,
        requested_capacity_percent=item.requested_capacity_percent,
        target_start_date=item.target_start_date,
        strategic_score=item.strategic_score,
        value_score=item.value_score,
        urgency_score=item.urgency_score,
        risk_score=item.risk_score,
        scoring_template_id=item.scoring_template_id,
        scoring_template_name=item.scoring_template_name,
        strategic_weight=item.strategic_weight,
        value_weight=item.value_weight,
        urgency_weight=item.urgency_weight,
        risk_weight=item.risk_weight,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
        version=item.version,
        composite_score=item.composite_score,
    )
