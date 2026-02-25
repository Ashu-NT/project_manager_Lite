from __future__ import annotations

from datetime import date

from core.exceptions import NotFoundError
from core.interfaces import (
    CostRepository,
    ProjectRepository,
    ProjectResourceRepository,
    ResourceRepository,
    TaskRepository,
)
from core.services.finance.analytics import build_dimension_analytics, build_source_analytics
from core.services.finance.cashflow import build_period_cashflow
from core.services.finance.helpers import normalize_currency
from core.services.finance.ledger import (
    build_computed_labor_actual_rows,
    build_computed_labor_plan_rows,
    build_cost_item_ledger_rows,
)
from core.services.finance.models import FinanceAnalyticsRow, FinanceLedgerRow, FinancePeriodRow, FinanceSnapshot
from core.services.finance.policy import manual_labor_raw_totals, resolve_manual_labor_inclusion
from core.services.reporting import ReportingService


class FinanceService:
    """Finance/commercial read models aligned with reporting cost policy."""

    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        resource_repo: ResourceRepository,
        cost_repo: CostRepository,
        project_resource_repo: ProjectResourceRepository,
        reporting_service: ReportingService,
    ) -> None:
        self._project_repo: ProjectRepository = project_repo
        self._task_repo: TaskRepository = task_repo
        self._resource_repo: ResourceRepository = resource_repo
        self._cost_repo: CostRepository = cost_repo
        self._project_resource_repo: ProjectResourceRepository = project_resource_repo
        self._reporting: ReportingService = reporting_service

    def get_finance_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
        period: str = "month",
    ) -> FinanceSnapshot:
        as_of = as_of or date.today()
        project = self._project_repo.get(project_id)
        if project is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        project_currency = normalize_currency(getattr(project, "currency", None), None)
        task_map = {task.id: task for task in self._task_repo.list_by_project(project_id)}
        resource_cache: dict[str, object | None] = {}
        source_breakdown = self._reporting.get_project_cost_source_breakdown(project_id, as_of=as_of)
        totals = self._reporting.get_project_cost_control_totals(project_id, as_of=as_of)
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
        ledger.extend(
            build_computed_labor_actual_rows(
                reporting_service=self._reporting,
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
