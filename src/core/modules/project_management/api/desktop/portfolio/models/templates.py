from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioTemplateDesktopDto:
    id: str
    name: str
    summary: str
    weight_summary: str
    is_active: bool
    strategic_weight: int
    value_weight: int
    urgency_weight: int
    risk_weight: int


__all__ = ["PortfolioTemplateDesktopDto"]
