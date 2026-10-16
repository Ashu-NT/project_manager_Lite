"""Neutral scoring-template response."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PortfolioTemplateResponseDto:
    id: str
    name: str
    summary: str
    is_active: bool
    strategic_weight: int
    value_weight: int
    urgency_weight: int
    risk_weight: int
