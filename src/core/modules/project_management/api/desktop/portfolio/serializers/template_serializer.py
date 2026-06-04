from src.core.modules.project_management.api.desktop.portfolio.models.templates import PortfolioTemplateDesktopDto


def serialize_template(template) -> PortfolioTemplateDesktopDto:
    return PortfolioTemplateDesktopDto(
        id=template.id,
        name=template.name,
        summary=template.summary or "",
        weight_summary=template.weight_summary,
        is_active=bool(template.is_active),
        strategic_weight=int(template.strategic_weight or 0),
        value_weight=int(template.value_weight or 0),
        urgency_weight=int(template.urgency_weight or 0),
        risk_weight=int(template.risk_weight or 0),
    )


__all__ = ["serialize_template"]
