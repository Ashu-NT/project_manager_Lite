from __future__ import annotations

from src.core.modules.project_management.domain.enums import (
    CostType,
    ResourceKind,
    WorkerType,
)


class TimeReportingEligibilityPolicy:
    """Single authoritative policy for Resource-owned labor timesheets."""

    ELIGIBLE_KINDS = frozenset({ResourceKind.PERSON})
    ELIGIBLE_WORKER_TYPES = frozenset({WorkerType.EMPLOYEE, WorkerType.EXTERNAL})
    ELIGIBLE_COST_TYPES = frozenset({CostType.LABOR})

    @classmethod
    def can_report_time(cls, resource: object) -> bool:
        return bool(
            getattr(resource, "is_active", False)
            and getattr(resource, "kind", None) in cls.ELIGIBLE_KINDS
            and getattr(resource, "worker_type", None) in cls.ELIGIBLE_WORKER_TYPES
            and getattr(resource, "cost_type", None) in cls.ELIGIBLE_COST_TYPES
        )


__all__ = ["TimeReportingEligibilityPolicy"]
