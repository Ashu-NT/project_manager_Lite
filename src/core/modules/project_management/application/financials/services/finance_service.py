from __future__ import annotations

from datetime import date

from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.contracts.repositories.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.task import TaskRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.cost_calendar import CostRepository
from src.core.platform.access.authorization import require_project_permission
from src.core.platform.auth.authorization import require_permission

from src.core.modules.project_management.application.financials.reporting.analytics import (
    build_dimension_analytics,
    build_source_analytics,
)
from src.core.modules.project_management.application.financials.cashflow.cashflow_builder import (
    build_period_cashflow,
)
from src.core.modules.project_management.application.financials.utils.helpers import (
    normalize_currency,
)
from src.core.modules.project_management.application.financials.costs.ledger import (
    build_computed_labor_actual_rows,
    build_computed_labor_plan_rows,
    build_cost_item_ledger_rows,
)
from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostPolicyEngine,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceAnalyticsRow,
    FinanceLedgerRow,
    FinancePeriodRow,
    FinanceSnapshot,
)
from src.core.modules.project_management.application.financials.costs.policy import (
    manual_labor_raw_totals,
    resolve_manual_labor_inclusion,
)
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


class FinanceService(ProjectManagementModuleGuardMixin):
    """Finance/commercial read models aligned with cost policy engine."""

    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        cost_repo: CostRepository,
        project_resource_repo: ProjectResourceRepository,
        reporting_service=None,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._cost_repo: CostRepository = cost_repo
        self._project_resource_repo: ProjectResourceRepository = project_resource_repo
        # reporting_service kept for duck-typed labor details access
        self._reporting = reporting_service
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def _make_cost_policy_engine(self) -> CostPolicyEngine:
        """Build a CostPolicyEngine with labor details provider wired in."""
        get_labor = None
        if self._reporting is not None:
            get_labor = self._reporting.get_project_labor_details
        return CostPolicyEngine(
            project_repo=self._project_repo,
            cost_repo=self._cost_repo,
            project_resource_repo=self._project_resource_repo,
            resource_repo=self._resource_repo,
            get_labor_details=get_labor,
        )

    def get_finance_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
        period: str = "month",
    ) -> FinanceSnapshot:
        require_permission(self._user_session, "report.view", operation_label="view finance snapshot")
        require_project_permission(
            self._user_session,
            project_id,
            "report.view",
            operation_label="view finance snapshot",
        )
        as_of = as_of or date.today()
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        project_currency = normalize_currency(getattr(project, "currency", None), None)
        task_map = {task.id: task for task in self._task_repo.list_by_project(project_id)}
        resource_cache: dict[str, object | None] = {}

        engine = self._make_cost_policy_engine()
        source_breakdown = engine.get_cost_source_breakdown(project_id, as_of=as_of)
        totals = engine.get_cost_control_totals(project_id, as_of=as_of)
        manual_raw = manual_labor_raw_totals(cost_repo=self._cost_repo, project_id=project_id, as_of=as_of)
        manual_included = resolve_manual_labor_inclusion(source_rows=source_breakdown.rows, manual_raw=manual_raw)

        ledger: list[FinanceLedgerRow] = []
        ledger.extend(
            build_cost_item_ledger_rows(
                cost_repo=self._cost_repo,
                project=project,
                task_map=task_map,
                as_of=as_of,
                manual_included=manual_included,
            )
        )
        ledger.extend(
            build_computed_labor_plan_rows(
                project_resource_repo=self._project_resource_repo,
                resource_repo=self._resource_repo,
                project=project,
                as_of=as_of,
                resource_cache=resource_cache,
            )
        )
        if self._reporting is not None:
            ledger.extend(
                build_computed_labor_actual_rows(
                    labor_provider=self._reporting,
                    project=project,
                    task_map=task_map,
                    as_of=as_of,
                )
            )
        ledger.sort(
            key=lambda row: (
                row.occurred_on or date.min,
                row.source_key,
                row.stage,
                row.reference_label.lower(),
            )
        )

        notes = list(source_breakdown.notes)
        notes.append(
            "Cashflow periods use each entry anchor date "
            "(cost incurred date, task date, or project start as fallback)."
        )

        return FinanceSnapshot(
            project_id=project_id,
            project_currency=totals.project_currency or project_currency,
            budget=float(totals.budget),
            planned=float(totals.planned),
            committed=float(totals.committed),
            actual=float(totals.actual),
            exposure=float(totals.exposure),
            available=(None if totals.available is None else float(totals.available)),
            ledger=ledger,
            cashflow=build_period_cashflow(ledger=ledger, period=period, as_of=as_of),
            by_source=build_source_analytics(source_breakdown.rows),
            by_cost_type=build_dimension_analytics(ledger=ledger, dimension="cost_type"),
            by_resource=build_dimension_analytics(ledger=ledger, dimension="resource"),
            by_task=build_dimension_analytics(ledger=ledger, dimension="task"),
            notes=notes,
        )

    def list_cost_ledger(self, project_id: str, *, as_of: date | None = None) -> list[FinanceLedgerRow]:
        return self.get_finance_snapshot(project_id, as_of=as_of).ledger

    def get_cashflow_by_period(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
        period: str = "month",
    ) -> list[FinancePeriodRow]:
        return self.get_finance_snapshot(project_id, as_of=as_of, period=period).cashflow

    def get_expense_analytics(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> dict[str, list[FinanceAnalyticsRow]]:
        snapshot = self.get_finance_snapshot(project_id, as_of=as_of)
        return {
            "source": snapshot.by_source,
            "cost_type": snapshot.by_cost_type,
            "resource": snapshot.by_resource,
            "task": snapshot.by_task,
        }


__all__ = ["FinanceService"]
