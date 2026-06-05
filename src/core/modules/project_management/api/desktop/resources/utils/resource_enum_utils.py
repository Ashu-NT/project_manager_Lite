from __future__ import annotations

from src.core.modules.project_management.domain.enums import CostType, WorkerType


def coerce_cost_type(value: str | CostType | None) -> CostType:
    if isinstance(value, CostType):
        return value
    normalized_value = str(value or CostType.LABOR.value).strip().upper()
    try:
        return CostType(normalized_value)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported resource category: {normalized_value}."
        ) from exc


def coerce_worker_type(value: str | WorkerType | None) -> WorkerType:
    if isinstance(value, WorkerType):
        return value
    normalized_value = str(value or WorkerType.EXTERNAL.value).strip().upper()
    try:
        return WorkerType(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Unsupported worker type: {normalized_value}.") from exc


__all__ = ["coerce_cost_type", "coerce_worker_type"]
