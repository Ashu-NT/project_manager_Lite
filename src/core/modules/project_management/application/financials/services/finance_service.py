from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import cast

from src.core.modules.project_management.access.scope_permissions import (
    require_project_permission,
)
from src.core.modules.project_management.application.common.module_guard import (
    ProjectManagementModuleGuardMixin,
)
from src.core.modules.project_management.application.financials.cost.engines.cost_policy_engine import (
    CostPolicyEngine,
)
from src.core.modules.project_management.application.financials.cost.engines.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.application.financials.cost.engines.ledger import (
    build_finance_ledger_rows,
)
from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceAnalyticsRow,
    FinanceLedgerRow,
    FinancePeriodRow,
    FinanceReconciliation,
    FinanceSnapshot,
)
from src.core.modules.project_management.application.financials.reporting.analytics import (
    build_dimension_analytics,
    build_source_analytics,
)
from src.core.modules.project_management.application.financials.utils.helpers import (
    normalize_currency,
)
from src.core.modules.project_management.contracts.reads.financials.finance_overview_reader import (
    FinanceOverviewReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_performance_reader import (
    FinancePerformanceReader,
)
from src.core.modules.project_management.contracts.reads.financials.finance_snapshot_reader import (
    FinanceSnapshotReader,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_overview_facts import (
    FinanceOverviewFacts,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_performance_facts import (
    CostPhasingQuery,
    CostPhasingSeriesAvailabilityFact,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    FinanceSnapshotFacts,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.platform.application.security.authorization.enforcement.permission_checks import (
    require_permission,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError


class FinanceService(ProjectManagementModuleGuardMixin):
    """Finance/commercial read models aligned with cost policy engine."""

    def __init__(
        self,
        *,
        rate_resolver: LaborRateResolver,
        finance_snapshot_reader: FinanceSnapshotReader,
        finance_performance_reader: FinancePerformanceReader,
        finance_overview_reader: FinanceOverviewReader | None = None,
        tenant_context_service: TenantContextService,
        user_session=None,
        module_catalog_service=None,
    ) -> None:
        self._finance_snapshot_reader: FinanceSnapshotReader = finance_snapshot_reader
        self._finance_performance_reader = finance_performance_reader
        self._finance_overview_reader = finance_overview_reader or cast(
            FinanceOverviewReader,
            finance_snapshot_reader,
        )
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

    def get_finance_overview(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> FinanceOverviewFacts:
        require_permission(
            self._user_session,
            "finance.read",
            operation_label="view finance overview",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view finance overview",
        )
        as_of = as_of or datetime.now(timezone.utc).astimezone().date()
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="build finance overview"
        )
        facts = self._finance_overview_reader.read_overview_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            as_of=as_of,
        )
        if facts is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        return facts

    def get_finance_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
        period: str = "month",
    ) -> FinanceSnapshot:
        require_permission(
            self._user_session, "finance.read", operation_label="view finance snapshot"
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.read",
            operation_label="view finance snapshot",
        )
        as_of = as_of or datetime.now(timezone.utc).astimezone().date()
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
        reconciliation = self._build_reconciliation(facts, ledger)
        if not reconciliation.is_reconciled:
            raise BusinessRuleError(
                "Finance controls do not reconcile to their canonical ledger sources.",
                code="FINANCE_RECONCILIATION_FAILED",
            )

        notes = list(source_breakdown.notes)
        notes.append(
            "This snapshot is a disposable read projection rebuilt from approved budget, "
            "approved forecast, posted actual, and open commitment authorities."
        )
        if facts.approved_forecast is None:
            notes.append(
                "No approved forecast exists at or before the as-of date; ETC, EAC, and VAC "
                "are intentionally unavailable."
            )
        else:
            notes.append(
                f"ETC uses approved forecast revision {facts.approved_forecast.revision} "
                f"as of {facts.approved_forecast.as_of_date.isoformat()}; open commitments "
                "are reported separately and are not added to EAC again."
            )
        notes.append(
            "Cost Phasing uses posting dates for actuals and approved forecast periods for ETC; it is not accounting cash flow."
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

        cost_phasing, cost_phasing_availability = self._read_canonical_cost_phasing(
            scope=scope,
            facts=facts,
            project_id=project_id,
            as_of=as_of,
        )

        return FinanceSnapshot(
            project_id=project_id,
            project_currency=(
                totals.project_currency
                or normalize_currency(facts.project.currency_code, None)
            ),
            budget=totals.budget,
            planned=totals.planned,
            committed=totals.committed,
            actual=totals.actual,
            forecast_etc=totals.forecast_etc,
            estimate_at_completion=totals.estimate_at_completion,
            budget_headroom=totals.budget_headroom,
            exposure=totals.exposure,
            available=totals.available,
            as_of=as_of,
            approved_budget_id=facts.project.approved_budget_id,
            approved_budget_revision=facts.project.approved_budget_revision,
            approved_forecast_id=(
                None
                if facts.approved_forecast is None
                else facts.approved_forecast.forecast_id
            ),
            approved_forecast_revision=(
                None
                if facts.approved_forecast is None
                else facts.approved_forecast.revision
            ),
            approved_forecast_as_of=(
                None
                if facts.approved_forecast is None
                else facts.approved_forecast.as_of_date
            ),
            currency_basis="PROJECT_CURRENCY",
            # Snapshot/report cost phasing is canonically monthly until a
            # dedicated report query exposes a second authoritative grain.
            period_granularity="month",
            sensitive_detail_included=can_read_sensitive,
            reconciliation=reconciliation,
            ledger=ledger,
            cost_phasing=cost_phasing,
            cost_phasing_availability=cost_phasing_availability,
            by_source=build_source_analytics(source_breakdown.rows),
            by_cost_type=build_dimension_analytics(
                ledger=ledger, dimension="cost_type"
            ),
            by_resource=(
                build_dimension_analytics(ledger=ledger, dimension="resource")
                if can_read_sensitive
                else []
            ),
            by_task=build_dimension_analytics(ledger=ledger, dimension="task"),
            notes=notes,
            unresolved_labor_rates=totals.unresolved_labor_rates,
        )

    def _read_canonical_cost_phasing(
        self, *, scope, facts, project_id: str, as_of: date
    ) -> tuple[list[FinancePeriodRow], tuple[CostPhasingSeriesAvailabilityFact, ...]]:
        date_from = facts.project.start_date or date(as_of.year, 1, 1)
        result = self._finance_performance_reader.read_cost_phasing(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            query=CostPhasingQuery(
                date_from=min(date_from, as_of),
                date_to=as_of,
                granularity="month",
                as_of_date=as_of,
            ),
        )
        if result is None:
            return [], ()
        return (
            [
                FinancePeriodRow(
                    period_key=item.period_key,
                    period_start=item.period_start,
                    period_end=item.period_end,
                    planned=item.planned_cost,
                    committed=item.open_commitment,
                    actual=item.posted_actual,
                    forecast=item.forecast_cost,
                    exposure=item.exposure,
                )
                for item in result.periods
            ],
            result.series_availability,
        )

    @staticmethod
    def _redact_sensitive_labor_rows(
        ledger: list[FinanceLedgerRow],
        *,
        project_id: str,
        as_of: date,
    ) -> list[FinanceLedgerRow]:
        visible: list[FinanceLedgerRow] = []
        grouped: dict[tuple[str, str, str, str | None], Decimal] = {}
        for row in ledger:
            if row.cost_type != "LABOR":
                visible.append(row)
                continue
            key = (row.source_key, row.source_label, row.stage, row.currency)
            grouped[key] = grouped.get(key, Decimal(0)) + row.amount

        for (source_key, source_label, stage, currency), amount in sorted(
            grouped.items(),
            key=lambda item: tuple(value or "" for value in item[0]),
        ):
            visible.append(
                FinanceLedgerRow(
                    project_id=project_id,
                    source_key=source_key,
                    source_label=source_label,
                    cost_type="LABOR",
                    stage=stage,
                    amount=amount,
                    currency=currency,
                    occurred_on=as_of,
                    reference_type="restricted_finance",
                    reference_id=(
                        f"restricted:{source_key}:{stage}:{currency or 'none'}"
                    ),
                    reference_label="Restricted labor cost",
                    task_id=None,
                    task_name=None,
                    resource_id=None,
                    resource_name=None,
                    cost_code_id=None,
                    source_type="restricted",
                    financial_period_id=None,
                    period_start=None,
                    period_end=None,
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

    @staticmethod
    def _build_reconciliation(
        facts: FinanceSnapshotFacts,
        ledger: list[FinanceLedgerRow],
    ) -> FinanceReconciliation:
        def stage_total(stage: str) -> Decimal:
            return sum(
                (row.amount for row in ledger if row.stage == stage),
                start=Decimal(0),
            )

        return FinanceReconciliation(
            posted_actual_control=facts.control.posted_actual,
            posted_actual_ledger=stage_total("actual"),
            open_commitment_control=facts.control.open_commitment,
            open_commitment_ledger=stage_total("committed"),
            forecast_etc_control=facts.control.forecast_etc,
            forecast_etc_ledger=(
                None if facts.control.forecast_etc is None else stage_total("forecast")
            ),
        )

    def get_finance_export_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
        period: str = "month",
    ) -> FinanceSnapshot:
        require_permission(
            self._user_session,
            "finance.export",
            operation_label="export project finance",
        )
        require_project_permission(
            self._user_session,
            project_id,
            "finance.export",
            operation_label="export project finance",
        )
        return self.get_finance_snapshot(project_id, as_of=as_of, period=period)

    def list_cost_ledger(
        self, project_id: str, *, as_of: date | None = None
    ) -> list[FinanceLedgerRow]:
        return self.get_finance_snapshot(project_id, as_of=as_of).ledger

    def get_cost_phasing_by_period(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
        period: str = "month",
    ) -> list[FinancePeriodRow]:
        return self.get_finance_snapshot(
            project_id, as_of=as_of, period=period
        ).cost_phasing

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
