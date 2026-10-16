from src.core.modules.project_management.api.desktop.portfolio.models.templates import (
    PortfolioTemplateDesktopDto,
)
from src.core.modules.project_management.application.portfolio.dto.responses.templates import (
    PortfolioTemplateResponseDto,
)


def serialize_template(template: PortfolioTemplateResponseDto) -> PortfolioTemplateDesktopDto:
    return PortfolioTemplateDesktopDto(
        id=template.id,
        name=template.name,
        summary=template.summary or "",
        weight_summary=(f"Strategic x{template.strategic_weight}, Value x{template.value_weight}, "
                        f"Urgency x{template.urgency_weight}, Risk x{template.risk_weight}"),
        is_active=bool(template.is_active),
        strategic_weight=int(template.strategic_weight or 0),
        value_weight=int(template.value_weight or 0),
        urgency_weight=int(template.urgency_weight or 0),
        risk_weight=int(template.risk_weight or 0),
    )


__all__ = ["serialize_template"]
