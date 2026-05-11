from __future__ import annotations

from core.modules.maintenance_management.domain import MaintenanceWorkRequestStatus

from src.core.platform.common.exceptions import ValidationError


class MaintenanceWorkRequestValidationMixin:
    def _validate_work_request_status_transition(
        self,
        current_status: MaintenanceWorkRequestStatus,
        new_status: MaintenanceWorkRequestStatus,
    ) -> None:
        """Validate that a work request status transition is allowed."""
        valid_transitions = {
            MaintenanceWorkRequestStatus.NEW: {
                MaintenanceWorkRequestStatus.TRIAGED,
                MaintenanceWorkRequestStatus.APPROVED,
                MaintenanceWorkRequestStatus.REJECTED,
                MaintenanceWorkRequestStatus.CONVERTED,
                MaintenanceWorkRequestStatus.DEFERRED,
            },
            MaintenanceWorkRequestStatus.TRIAGED: {
                MaintenanceWorkRequestStatus.APPROVED,
                MaintenanceWorkRequestStatus.REJECTED,
                MaintenanceWorkRequestStatus.CONVERTED,
                MaintenanceWorkRequestStatus.DEFERRED,
            },
            MaintenanceWorkRequestStatus.APPROVED: {
                MaintenanceWorkRequestStatus.CONVERTED,
                MaintenanceWorkRequestStatus.DEFERRED,
            },
            MaintenanceWorkRequestStatus.REJECTED: set(),
            MaintenanceWorkRequestStatus.CONVERTED: set(),
            MaintenanceWorkRequestStatus.DEFERRED: {
                MaintenanceWorkRequestStatus.TRIAGED,
                MaintenanceWorkRequestStatus.APPROVED,
                MaintenanceWorkRequestStatus.REJECTED,
                MaintenanceWorkRequestStatus.CONVERTED,
            },
        }

        if new_status not in valid_transitions.get(current_status, set()):
            raise ValidationError(
                f"Cannot change work request status from {current_status.value} to {new_status.value}.",
                code="MAINTENANCE_WORK_REQUEST_STATUS_INVALID_TRANSITION",
            )

__all__ = [
    "MaintenanceWorkRequestValidationMixin",
]