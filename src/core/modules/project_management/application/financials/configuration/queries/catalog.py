from __future__ import annotations

from datetime import date

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import (
    ProjectCostCodeRepository,
    ProjectFinancialProfileRepository,
)
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
)
from src.core.modules.project_management.domain.financials.configuration import (
    CostCodePolicy,
    ProjectCostCode,
    ProjectFinancialProfile,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class FinancialConfigurationQueryHandler(ProjectManagementModuleGuardMixin):
    """Authorized financial profile and effective cost-code catalog reads."""

    def __init__(
        self,
        *,
        profile_repo: ProjectFinancialProfileRepository,
        cost_code_repo: ProjectCostCodeRepository,
        project_repo: ProjectRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._profile_repo = profile_repo
        self._cost_code_repo = cost_code_repo
        self._project_repo = project_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_profile(self, project_id: str) -> ProjectFinancialProfile:
        self._require_project(project_id, "finance.read", "view financial profile")
        return self._require_profile(project_id)

    def list_cost_codes(self, *, include_inactive: bool = False) -> list[ProjectCostCode]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list project cost codes",
        )
        return self._cost_code_repo.list(include_inactive=include_inactive)

    def list_available_cost_codes(
        self,
        project_id: str,
        *,
        effective_on: date | None = None,
    ) -> list[ProjectCostCode]:
        self._require_project(project_id, "finance.read", "list available project cost codes")
        profile = self._require_profile(project_id)
        rows = self._cost_code_repo.list(include_inactive=False)
        if profile.cost_code_policy == CostCodePolicy.RESTRICTED:
            allowed_ids = {
                row.cost_code_id for row in self._cost_code_repo.list_restrictions(project_id)
            }
            rows = [row for row in rows if row.id in allowed_ids]
        as_of = effective_on or date.today()  # noqa: DTZ011 -- naive local business date by design
        return [row for row in rows if row.is_effective_on(as_of)]

    def _require_project(self, project_id: str, permission: str, operation: str):
        require_permission(self._user_session, permission, operation_label=operation)
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.")
        require_project_permission(
            self._user_session,
            project_id,
            permission,
            operation_label=operation,
        )
        return project

    def _require_profile(self, project_id: str) -> ProjectFinancialProfile:
        profile = self._profile_repo.get_by_project(project_id)
        if profile is None:
            raise NotFoundError(
                "Project financial profile not found.",
                code="FINANCIAL_PROFILE_NOT_FOUND",
            )
        return profile


__all__ = ["FinancialConfigurationQueryHandler"]
