from __future__ import annotations

from core.modules.maintenance_management.domain import MaintenanceWorkOrderTaskStepStatus
from core.platform.common.exceptions import ValidationError


class MaintenanceWorkOrderTaskStepValidationMixin:
    def _validate_work_order_task_step_status_transition(
        self,
        current_status: MaintenanceWorkOrderTaskStepStatus,
        new_status: MaintenanceWorkOrderTaskStepStatus,
    ) -> None:
        valid_transitions = {
            MaintenanceWorkOrderTaskStepStatus.NOT_STARTED: {
                MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS,
                MaintenanceWorkOrderTaskStepStatus.DONE,
                MaintenanceWorkOrderTaskStepStatus.SKIPPED,
                MaintenanceWorkOrderTaskStepStatus.FAILED,
            },
            MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS: {
                MaintenanceWorkOrderTaskStepStatus.DONE,
                MaintenanceWorkOrderTaskStepStatus.SKIPPED,
                MaintenanceWorkOrderTaskStepStatus.FAILED,
            },
            MaintenanceWorkOrderTaskStepStatus.FAILED: {
                MaintenanceWorkOrderTaskStepStatus.IN_PROGRESS,
                MaintenanceWorkOrderTaskStepStatus.SKIPPED,
            },
            MaintenanceWorkOrderTaskStepStatus.DONE: set(),
            MaintenanceWorkOrderTaskStepStatus.SKIPPED: set(),
        }

        if new_status not in valid_transitions.get(current_status, set()):
            raise ValidationError(
                f"Cannot change work order task step status from {current_status.value} to {new_status.value}.",
                code="MAINTENANCE_WORK_ORDER_TASK_STEP_STATUS_INVALID_TRANSITION",
            )


__all__ = ["MaintenanceWorkOrderTaskStepValidationMixin"]
