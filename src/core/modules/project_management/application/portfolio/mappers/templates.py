"""Map scoring-template state without display summaries."""

from src.core.modules.project_management.application.portfolio.dto.responses.templates import (
    PortfolioTemplateResponseDto,
)
from src.core.modules.project_management.domain.portfolio import (
    PortfolioScoringTemplate,
)


def map_template(template: PortfolioScoringTemplate) -> PortfolioTemplateResponseDto:
    return PortfolioTemplateResponseDto(
        id=template.id, name=template.name, summary=template.summary or "",
        is_active=bool(template.is_active), strategic_weight=int(template.strategic_weight or 0),
        value_weight=int(template.value_weight or 0), urgency_weight=int(template.urgency_weight or 0),
        risk_weight=int(template.risk_weight or 0),
    )
