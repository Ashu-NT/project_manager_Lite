from __future__ import annotations

from src.core.modules.project_management.application.risk import (
    RegisterDashboardSnapshot,
    RegisterQueryHandler,
)
from src.core.platform.common.exceptions import BusinessRuleError


class DashboardRegisterWidget:
    def __init__(self, register_query: RegisterQueryHandler | None) -> None:
        self._registers = register_query

    def build_snapshot(self, project_id: str) -> RegisterDashboardSnapshot | None:
        if self._registers is None:
            return None
        try:
            return self._registers.get_dashboard_snapshot(project_id)
        except BusinessRuleError:
            return None


__all__ = ["DashboardRegisterWidget"]
