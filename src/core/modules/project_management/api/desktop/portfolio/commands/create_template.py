from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioTemplateCreateCommand:
    name: str
    summary: str = ""
    strategic_weight: int = 3
    value_weight: int = 2
    urgency_weight: int = 2
    risk_weight: int = 1
    activate: bool = False


__all__ = ["PortfolioTemplateCreateCommand"]
