"""Cost type coercion utilities."""

from __future__ import annotations
from src.core.modules.project_management.domain.enums import CostType


def coerce_cost_type(value: str | CostType | None) -> CostType:
    if isinstance(value, CostType):
        return value
    normalized = str(value or CostType.OVERHEAD.value).strip().upper()
    try:
        return CostType(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported cost type: {normalized}.") from exc


__all__ = ["coerce_cost_type"]
