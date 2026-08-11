from __future__ import annotations

from datetime import date

from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.contracts.repositories.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.contracts.reads.financials.finance_snapshot_reader import (
    FinanceSnapshotReader,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.modules.project_management.access.scope_permissions import require_project_permission
from src.core.platform.application.security.authorization.enforcement.permission_checks import require_permission

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
    build_finance_ledger_rows,
)
from src.core.modules.project_management.application.financials.costs.cost_policy_engine import (
    CostPolicyEngine,
)
from src.core.modules.project_management.application.financials.costs.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceAnalyticsRow,
    FinanceLedgerRow,
    FinancePeriodRow,
    FinanceSnapshot,
)
from src.core.modules.project_management.application.common.module_guard import ProjectManagementModuleGuardMixin


class FinanceService(ProjectManagementModuleGuardMixin):
    """Finance/commercial read models aligned with cost policy engine."""

    def __init__(
        self,
        *,
        rate_resolver: LaborRateResolver,
        finance_snapshot_reader: FinanceSnapshotReader,
        tenant_context_service: TenantContextService,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._finance_snapshot_reader: FinanceSnapshotReader = finance_snapshot_reader
        self._tenant_context_service: TenantContextService = tenant_context_service
        self._labor = LaborCostEngine.for_facts(
            rate_resolver=rate_resolver,
            tenant_context_service=tenant_context_service,
        )
        self._cost_policy = CostPolicyEngine.for_facts(
            rate_resolver=rate_resolver,
            tenant_context_service=tenant_context_service,
        )
        self._user_session = user_session
        self._module_catalog_service = module_catalog_service

    def get_finance_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
        period: str = "month",
    ) -> FinanceSnapshot:
        require_permission(self._user_session, "finance.read", operation_label="view finance snapshot")
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view finance snapshot",
        )
        as_of = as_of or date.today()
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="build finance snapshot"
        )
        facts = self._finance_snapshot_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            as_of=as_of,
        )
        if facts is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")

        labor_details = self._labor.calculate_project_labor_details(
            project_id,
            as_of,
            facts=facts,
        )
        policy = self._cost_policy.compose_from_facts(facts, labor_details)
        source_breakdown = policy.source_breakdown
        totals = policy.totals

        ledger = build_finance_ledger_rows(facts=facts)
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
        can_read_sensitive = bool(
            self._user_session is not None
            and self._user_session.has_project_permission(
                project_id,
                "finance.read_sensitive",
            )
        )
        if not can_read_sensitive:
            ledger = self._redact_sensitive_labor_rows(
                ledger,
                project_id=project_id,
                as_of=as_of,
            )
            notes.append(
                "Detailed labor finance data is hidden because finance.read_sensitive "
                "is not granted."
            )

        return FinanceSnapshot(
            project_id=project_id,
            project_currency=(
                totals.project_currency
                or normalize_currency(facts.project.currency, None)
            ),
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
            by_resource=(
                build_dimension_analytics(ledger=ledger, dimension="resource")
                if can_read_sensitive
                else []
            ),
            by_task=build_dimension_analytics(ledger=ledger, dimension="task"),
            notes=notes,
            unresolved_labor_rates=totals.unresolved_labor_rates,
        )

    @staticmethod
    def _redact_sensitive_labor_rows(
        ledger: list[FinanceLedgerRow],
        *,
        project_id: str,
        as_of: date,
    ) -> list[FinanceLedgerRow]:
        visible: list[FinanceLedgerRow] = []
        grouped: dict[tuple[str, str | None], float] = {}
        for row in ledger:
            if row.source_key != "APPROVED_TIME":
                visible.append(row)
                continue
            key = (row.stage, row.currency)
            grouped[key] = grouped.get(key, 0.0) + float(row.amount)

        for (stage, currency), amount in sorted(
            grouped.items(),
            key=lambda item: (item[0][0], item[0][1] or ""),
        ):
            visible.append(
                FinanceLedgerRow(
                    project_id=project_id,
                    source_key="APPROVED_TIME",
                    source_label="Approved Time",
                    cost_type="LABOR",
                    stage=stage,
                    amount=amount,
                    currency=currency,
                    occurred_on=as_of,
                    reference_type="restricted_finance",
                    reference_id=f"restricted:{stage}:{currency or 'none'}",
                    reference_label="Restricted labor cost",
                    task_id=None,
                    task_name=None,
                    resource_id=None,
                    resource_name=None,
                    included_in_policy=True,
                )
            )
        visible.sort(
            key=lambda row: (
                row.occurred_on or date.min,
                row.source_key,
                row.stage,
                row.reference_label.lower(),
            )
        )
        return visible

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
