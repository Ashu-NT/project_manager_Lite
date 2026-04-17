from __future__ import annotations

from core.platform.common.exceptions import NotFoundError
from core.modules.project_management.domain.cost import CostItem
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission


class CostQueryMixin:
    def list_cost_items_for_project(self, project_id: str) -> list[CostItem]:
        require_permission(self._user_session, "cost.read", operation_label="list project costs")
        require_project_permission(
            self._user_session,
            project_id,
            "cost.read",
            operation_label="list project costs",
        )
        return self._cost_repo.list_by_project(project_id)

    def get_project_cost_summary(self, project_id: str) -> dict:
        require_permission(self._user_session, "cost.read", operation_label="view project cost summary")
        require_project_permission(
            self._user_session,
            project_id,
            "cost.read",
            operation_label="view project cost summary",
        )
        if not self._project_repo.get(project_id):
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        items = self._cost_repo.list_by_project(project_id)
        total_planned = sum(item.planned_amount for item in items)
        total_committed = sum(item.committed_amount for item in items)
        total_actual = sum(item.actual_amount for item in items)
        variance = total_actual - total_planned
        committed_variance = total_committed - total_planned

        # Keep both legacy and normalized keys for backwards compatibility.
        return {
            "project_id": project_id,
            "total_planned": total_planned,
            "total_committed": total_committed,
            "total-committed": total_committed,
            "total_actual": total_actual,
            "variance": variance,
            "variance_actual": variance,
            "variance_commitment": committed_variance,
            "variance_committment": committed_variance,
            "exposure": total_committed + total_actual,
            "items_count": len(items),
        }
