from __future__ import annotations

from decimal import Decimal


from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.planned_costs.planned_cost import (
    ProjectPlannedCostVersionRepository,
)
from src.core.modules.project_management.domain.financials.planned_cost import (
    ProjectPlannedCostLine,
    ProjectPlannedCostVersion,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import (
    NotFoundError,
)


class PlannedCostQueryHandler(ProjectManagementModuleGuardMixin):
    """Authorized reads for planned cost query handler."""

    def __init__(
        self,
        *,
        planned_cost_repo: ProjectPlannedCostVersionRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._planned_cost_repo = planned_cost_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_current_snapshot(self, project_id: str) -> ProjectPlannedCostVersion | None:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view planned-cost snapshot",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view planned-cost snapshot",
        )
        return self._planned_cost_repo.get_current_for_project(project_id)

    def list_versions(self, project_id: str) -> list[ProjectPlannedCostVersion]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list planned-cost snapshots",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="list planned-cost snapshots",
        )
        return self._planned_cost_repo.list_for_project(project_id)

    def get_version(self, version_id: str) -> ProjectPlannedCostVersion:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view planned-cost snapshot",
        )
        version = self._require_version(version_id)
        require_project_permission(
            self._user_session,
            version.project_id,
            "finance.read",
            operation_label="view planned-cost snapshot",
        )
        return version

    def list_lines(self, version_id: str) -> list[ProjectPlannedCostLine]:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="list planned-cost lines",
        )
        version = self._require_version(version_id)
        require_project_permission(
            self._user_session,
            version.project_id,
            "finance.read",
            operation_label="list planned-cost lines",
        )
        return self._planned_cost_repo.list_lines(version_id)

    def get_totals_by_cost_code(self, version_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(version_id):
            totals[line.cost_code_id] = (
                totals.get(line.cost_code_id, Decimal(0)) + line.amount
            )
        return totals

    def get_totals_by_task(self, version_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(version_id):
            totals[line.task_id] = totals.get(line.task_id, Decimal(0)) + line.amount
        return totals

    # -- Calculation ------------------------------------------------------

    def _require_version(self, version_id: str) -> ProjectPlannedCostVersion:
        version = self._planned_cost_repo.get(version_id)
        if version is None:
            raise NotFoundError(
                "Planned-cost version not found.", code="PLANNED_COST_VERSION_NOT_FOUND"
            )
        return version


__all__ = ["PlannedCostQueryHandler"]
