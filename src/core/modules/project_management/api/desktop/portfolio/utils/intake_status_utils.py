"""Intake status coercion utilities."""

from __future__ import annotations
from src.core.modules.project_management.domain.portfolio import PortfolioIntakeStatus


def coerce_intake_status(value: str | PortfolioIntakeStatus | None) -> PortfolioIntakeStatus:
    if isinstance(value, PortfolioIntakeStatus):
        return value
    normalized = str(value or PortfolioIntakeStatus.PROPOSED.value).strip().upper()
    try:
        return PortfolioIntakeStatus(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported portfolio intake status: {normalized}.") from exc


__all__ = ["coerce_intake_status"]
