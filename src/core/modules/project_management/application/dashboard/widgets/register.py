from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError
from src.core.modules.project_management.application.risk import (
    RegisterDashboardSnapshot,
    RegisterService,
)


class DashboardRegisterMixin:
    _registers: RegisterService | None

    def _build_register_snapshot(
        self,
        project_id: str,
    ) -> RegisterDashboardSnapshot | None:
        if self._registers is None:
            return None
        try:
            return self._registers.get_dashboard_snapshot(project_id)
        except BusinessRuleError:
            return None


__all__ = ["DashboardRegisterMixin"]
