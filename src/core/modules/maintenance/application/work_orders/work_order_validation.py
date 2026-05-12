from __future__ import annotations

from core.modules.maintenance_management.domain import MaintenanceWorkOrderStatus

from src.core.platform.common.exceptions import ValidationError

class MaintenanceWorkOrderValidationMixin:
    def _validate_work_order_status_transition(
        self,
        current_status: MaintenanceWorkOrderStatus,
        new_status: MaintenanceWorkOrderStatus,
    ) -> None:
        """Validate that a work order status transition is allowed."""
        valid_transitions = {
            MaintenanceWorkOrderStatus.DRAFT: {
                MaintenanceWorkOrderStatus.PLANNED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.PLANNED: {
                MaintenanceWorkOrderStatus.WAITING_PARTS,
                MaintenanceWorkOrderStatus.WAITING_APPROVAL,
                MaintenanceWorkOrderStatus.WAITING_SHUTDOWN,
                MaintenanceWorkOrderStatus.SCHEDULED,
                MaintenanceWorkOrderStatus.RELEASED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.WAITING_PARTS: {
                MaintenanceWorkOrderStatus.PLANNED,
                MaintenanceWorkOrderStatus.SCHEDULED,
                MaintenanceWorkOrderStatus.RELEASED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.WAITING_APPROVAL: {
                MaintenanceWorkOrderStatus.PLANNED,
                MaintenanceWorkOrderStatus.SCHEDULED,
                MaintenanceWorkOrderStatus.RELEASED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.WAITING_SHUTDOWN: {
                MaintenanceWorkOrderStatus.PLANNED,
                MaintenanceWorkOrderStatus.SCHEDULED,
                MaintenanceWorkOrderStatus.RELEASED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.SCHEDULED: {
                MaintenanceWorkOrderStatus.RELEASED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.RELEASED: {
                MaintenanceWorkOrderStatus.IN_PROGRESS,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.IN_PROGRESS: {
                MaintenanceWorkOrderStatus.PAUSED,
                MaintenanceWorkOrderStatus.COMPLETED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.PAUSED: {
                MaintenanceWorkOrderStatus.IN_PROGRESS,
                MaintenanceWorkOrderStatus.COMPLETED,
                MaintenanceWorkOrderStatus.CANCELLED,
            },
            MaintenanceWorkOrderStatus.COMPLETED: {
                MaintenanceWorkOrderStatus.VERIFIED,
                MaintenanceWorkOrderStatus.CLOSED,
            },
            MaintenanceWorkOrderStatus.VERIFIED: {
                MaintenanceWorkOrderStatus.CLOSED,
            },
            MaintenanceWorkOrderStatus.CLOSED: set(),
            MaintenanceWorkOrderStatus.CANCELLED: set(),
        }

        if new_status not in valid_transitions.get(current_status, set()):
            raise ValidationError(
                f"Cannot change work order status from {current_status.value} to {new_status.value}.",
                code="MAINTENANCE_WORK_ORDER_STATUS_INVALID_TRANSITION",
            )


__all__ = [
    "MaintenanceWorkOrderValidationMixin",
]