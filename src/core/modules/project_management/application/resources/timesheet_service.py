from __future__ import annotations

from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.platform.time.application import TimeService


class TimesheetService(
    ProjectManagementModuleGuardMixin,
    TimeService,
):
    """Project-management timesheet workflows backed by shared platform time logic."""


__all__ = ["TimesheetService"]
