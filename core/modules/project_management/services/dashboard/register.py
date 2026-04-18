from __future__ import annotations

from src.core.platform.common.exceptions import BusinessRuleError
from core.modules.project_management.services.register import RegisterService
from core.modules.project_management.services.register.models import RegisterProjectSummary


class DashboardRegisterMixin:
    _registers: RegisterService | None

    def _build_register_summary(self, project_id: str) -> RegisterProjectSummary | None:
        if self._registers is None:
            return None
        try:
            return self._registers.get_project_summary(project_id)
        except BusinessRuleError:
            return None


__all__ = ["DashboardRegisterMixin"]
