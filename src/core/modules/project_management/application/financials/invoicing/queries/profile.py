from __future__ import annotations

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.invoicing.billing import (
    ProjectBillingRepository,
)
from src.core.modules.project_management.domain.financials.billing_profile import (
    ProjectBillingProfile,
    ProjectBillingScheduleLine,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)


class ProjectBillingProfileQueryHandler(ProjectManagementModuleGuardMixin):
    """Read project commercial terms and billing schedules."""

    def __init__(self, *, billing_repo: ProjectBillingRepository, user_session=None, module_catalog_service=None) -> None:
        self._billing_repo = billing_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_profile(self, project_id: str) -> ProjectBillingProfile | None:
        self._require(project_id, "finance.read", "view project billing profile")
        return self._billing_repo.get_profile(project_id)

    def list_schedule(self, project_id: str) -> list[ProjectBillingScheduleLine]:
        self._require(project_id, "finance.read", "view project billing schedule")
        return self._billing_repo.list_schedule_lines(project_id)

    def _require(self, project_id: str, permission: str, operation: str) -> None:
        require_permission(self._user_session, permission, operation_label=operation)
        require_project_permission(
            self._user_session, project_id, permission, operation_label=operation
        )

__all__ = ["ProjectBillingProfileQueryHandler"]
