from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.contracts.repositories.finance.budgets.budget import (
    ProjectBudgetRepository,
)
from src.core.modules.project_management.domain.financials.budget import (
    BudgetLine,
    ProjectBudget,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.common.exceptions import NotFoundError


class BudgetQueries(ProjectManagementModuleGuardMixin):
    """Authorized aggregate reads, independent of lifecycle command dependencies."""

    def __init__(
        self,
        *,
        budget_repo: ProjectBudgetRepository,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._budget_repo = budget_repo
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_budget(self, budget_id: str) -> ProjectBudget:
        require_permission(self._user_session, "finance.read", operation_label="view project budget")
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session, budget.project_id, "finance.read", operation_label="view project budget"
        )
        return budget

    def list_budgets_for_project(
        self, project_id: str, *, include_superseded: bool = True
    ) -> list[ProjectBudget]:
        require_permission(self._user_session, "finance.read", operation_label="list project budgets")
        require_project_permission(
            self._user_session, project_id, "finance.read", operation_label="list project budgets"
        )
        return self._budget_repo.list_for_project(project_id, include_superseded=include_superseded)

    def get_approved_budget(self, project_id: str) -> ProjectBudget | None:
        require_permission(
            self._user_session, "finance.read", operation_label="view approved project budget"
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view approved project budget",
        )
        return self._budget_repo.get_approved_for_project(project_id)

    def list_lines(self, budget_id: str) -> list[BudgetLine]:
        require_permission(
            self._user_session, "finance.read", operation_label="list project budget lines"
        )
        budget = self._require_budget(budget_id)
        require_project_permission(
            self._user_session,
            budget.project_id,
            "finance.read",
            operation_label="list project budget lines",
        )
        return self._budget_repo.list_lines(budget_id)

    def get_totals_by_cost_code(self, budget_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(budget_id):
            totals[line.cost_code_id] = totals.get(line.cost_code_id, Decimal(0)) + line.amount
        return totals

    def get_totals_by_task(self, budget_id: str) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for line in self.list_lines(budget_id):
            key = line.task_id or ""
            totals[key] = totals.get(key, Decimal(0)) + line.amount
        return totals

    def _require_budget(self, budget_id: str) -> ProjectBudget:
        budget = self._budget_repo.get(budget_id)
        if budget is None:
            raise NotFoundError("Project budget not found.", code="PROJECT_BUDGET_NOT_FOUND")
        return budget


__all__ = ["BudgetQueries"]
