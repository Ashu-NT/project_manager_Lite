from __future__ import annotations

from src.core.modules.project_management.application.resources.task_assignment_capacity_service import (
    CAPACITY_AVAILABLE,
    CAPACITY_NEAR_CAPACITY,
    CAPACITY_OVER_CAPACITY,
    CAPACITY_UNKNOWN,
)

_CAPACITY_STATUS_LABELS = {
    CAPACITY_AVAILABLE: "Within capacity",
    CAPACITY_NEAR_CAPACITY: "Near capacity",
    CAPACITY_OVER_CAPACITY: "Over capacity",
    CAPACITY_UNKNOWN: "Capacity unknown",
}


def capacity_status_label(capacity_status: str) -> str:
    """Single source of display text for the authoritative capacity_status
    vocabulary (docs §44/§53) -- reused by both the assignment list preview
    and the create/edit preview so the same backend status never renders as
    two different words in two different places."""
    return _CAPACITY_STATUS_LABELS.get(capacity_status, "Capacity unknown")


__all__ = ["capacity_status_label"]
