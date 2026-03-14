from __future__ import annotations

from core.modules.project_management.services.common.module_guard import ProjectManagementModuleGuardMixin
from core.platform.time import TimeService


class TimesheetService(
    ProjectManagementModuleGuardMixin,
    TimeService,
):
    """Project-management wrapper over the shared platform time service."""


__all__ = ["TimesheetService"]
