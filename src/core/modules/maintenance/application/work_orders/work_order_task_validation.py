from __future__ import annotations

from core.modules.maintenance_management.domain import MaintenanceWorkOrderTaskStatus
from src.core.platform.common.exceptions import ValidationError


class MaintenanceWorkOrderTaskValidationMixin:
    def _validate_work_order_task_status_transition(
        self,
        current_status: MaintenanceWorkOrderTaskStatus,
        new_status: MaintenanceWorkOrderTaskStatus,
    ) -> None:
        valid_transitions = {
            MaintenanceWorkOrderTaskStatus.NOT_STARTED: {
                MaintenanceWorkOrderTaskStatus.IN_PROGRESS,
                MaintenanceWorkOrderTaskStatus.COMPLETED,
                MaintenanceWorkOrderTaskStatus.BLOCKED,
                MaintenanceWorkOrderTaskStatus.SKIPPED,
            },
            MaintenanceWorkOrderTaskStatus.IN_PROGRESS: {
                MaintenanceWorkOrderTaskStatus.COMPLETED,
                MaintenanceWorkOrderTaskStatus.BLOCKED,
                MaintenanceWorkOrderTaskStatus.SKIPPED,
            },
            MaintenanceWorkOrderTaskStatus.BLOCKED: {
                MaintenanceWorkOrderTaskStatus.IN_PROGRESS,
                MaintenanceWorkOrderTaskStatus.SKIPPED,
            },
            MaintenanceWorkOrderTaskStatus.COMPLETED: set(),
            MaintenanceWorkOrderTaskStatus.SKIPPED: set(),
        }

        if new_status not in valid_transitions.get(current_status, set()):
            raise ValidationError(
                f"Cannot change work order task status from {current_status.value} to {new_status.value}.",
                code="MAINTENANCE_WORK_ORDER_TASK_STATUS_INVALID_TRANSITION",
            )


__all__ = ["MaintenanceWorkOrderTaskValidationMixin"]
