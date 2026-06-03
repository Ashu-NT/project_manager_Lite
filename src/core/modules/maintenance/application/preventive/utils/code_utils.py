"""Code and description generation helpers for preventive plans."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from src.core.platform.common.ids import generate_id

if TYPE_CHECKING:
    from src.core.modules.maintenance.application.preventive.models.candidates import (
        MaintenancePreventiveDueCandidate,
    )
    from src.core.modules.maintenance.domain import MaintenancePreventivePlan


_PLAN_TYPE_TO_WORK_ORDER_TYPE: dict[str, str] = {
    "PREVENTIVE": "PREVENTIVE",
    "INSPECTION": "INSPECTION",
    "CALIBRATION": "CALIBRATION",
    "LUBRICATION": "PREVENTIVE",
    "CONDITION_BASED": "CONDITION_BASED",
}


def map_plan_to_work_order_type(plan: "MaintenancePreventivePlan") -> str:
    """Map a preventive plan type to its corresponding work order type."""
    return _PLAN_TYPE_TO_WORK_ORDER_TYPE.get(plan.plan_type.value, "PREVENTIVE")


def build_generated_code(base_code: str, *, suffix: str) -> str:
    """Build a unique generated code like PLAN-001-WO-A3F7B2C1."""
    token = generate_id().replace("-", "")[:8].upper()
    return f"{base_code}-{suffix}-{token}"


def build_generation_description(
    plan: "MaintenancePreventivePlan",
    candidate: "MaintenancePreventiveDueCandidate",
    as_of: datetime,
) -> str:
    """Build the description text for a generated work request or work order."""
    return (
        f"Generated from preventive plan {plan.plan_code} on {as_of.isoformat()}."
        f" Trigger reason: {candidate.due_reason}"
    )


__all__ = [
    "build_generated_code",
    "build_generation_description",
    "map_plan_to_work_order_type",
]
