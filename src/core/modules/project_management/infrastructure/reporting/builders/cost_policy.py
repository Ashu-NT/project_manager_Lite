"""Cost policy mixin — thin reporting delegate.

Business logic lives in financials/costs/cost_policy_engine.py.
This mixin wires the reporting service's repos into CostPolicyEngine
so that all cost-policy calculations use a single authoritative implementation.
"""

from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.contracts.reads.financials import (
    EvmSeriesFacts,
    EvmSeriesReader,
    FinanceSnapshotFacts,
    FinanceSnapshotReader,
)
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService
from src.core.platform.common.exceptions import NotFoundError
from src.core.modules.project_management.application.financials.cost.engines.cost_policy_engine import (
    CostControlTotals,
    CostPolicyComposition,
    CostPolicyEngine,
    CostPolicySnapshot,
)
from src.core.modules.project_management.application.financials.cost.engines.labor_cost import (
    LaborCostEngine,
)

# Re-export so existing imports of these from reporting.builders.cost_policy still work.
from src.core.modules.project_management.infrastructure.reporting.models.report_models import (
    CostSourceBreakdown,
    CostSourceRow,
)

CostBucketKey = tuple[CostType, str]


class ReportingCostPolicyMixin:
    """Thin delegate — all logic lives in CostPolicyEngine (financials)."""

    _rate_resolver: LaborRateResolver
    _tenant_context_service: TenantContextService
    _finance_snapshot_reader: FinanceSnapshotReader
    _evm_series_reader: EvmSeriesReader

    def _make_cost_policy_engine(self) -> CostPolicyEngine:
        return CostPolicyEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        )

    def _build_cost_policy_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostPolicySnapshot:
        return self._compose_finance_policy(
            project_id, as_of=as_of or date.today()
        )[1].snapshot

    def get_project_cost_control_totals(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostControlTotals:
        self._require_finance_view("view cost control totals", project_id=project_id)
        _, policy = self._compose_finance_policy(
            project_id,
            as_of=as_of or date.today(),
        )
        return policy.totals

    def get_project_cost_source_breakdown(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostSourceBreakdown:
        self._require_finance_view("view cost source breakdown", project_id=project_id)
        _, policy = self._compose_finance_policy(
            project_id,
            as_of=as_of or date.today(),
        )
        return policy.source_breakdown

    def _compose_finance_policy(
        self,
        project_id: str,
        *,
        as_of: date,
    ) -> tuple[FinanceSnapshotFacts, CostPolicyComposition]:
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="read reporting financial facts"
        )
        facts = self._finance_snapshot_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            as_of=as_of,
        )
        if facts is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        labor = LaborCostEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        ).calculate_project_labor_details(
            project_id,
            as_of,
            facts=facts,
        )
        policy = CostPolicyEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        ).compose_from_facts(facts, labor)
        return facts, policy

    def _compose_evm_policy(
        self,
        project_id: str,
        *,
        baseline_id: str | None,
        as_of: date,
    ) -> tuple[EvmSeriesFacts, CostPolicyComposition]:
        scope = self._tenant_context_service.require_active_scope_ids(
            operation_label="read reporting EVM facts"
        )
        facts = self._evm_series_reader.read_facts(
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            project_id=project_id,
            baseline_id=baseline_id,
            as_of=as_of,
        )
        if facts is None:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        labor = LaborCostEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        ).calculate_project_labor_details(
            project_id,
            as_of,
            facts=facts.finance,
        )
        policy = CostPolicyEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        ).compose_from_facts(facts.finance, labor)
        return facts, policy

    # Proxy helpers for mixins that call self._xxx() ─────────────────────────

    def _normalize_currency(self, value: str | None, fallback: str | None = None) -> str:
        return self._make_cost_policy_engine()._normalize_currency(value, fallback)

    def _add_bucket(
        self,
        target: dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        currency: str,
        amount: float,
    ) -> None:
        self._make_cost_policy_engine()._add_bucket(
            target, cost_type=cost_type, currency=currency, amount=amount
        )

    def _sum_bucket_map(
        self,
        values: dict[CostBucketKey, float],
        project_currency: str | None,
    ) -> float:
        return self._make_cost_policy_engine()._sum_bucket_map(values, project_currency)

    def _sum_bucket_for_type(
        self,
        values: dict[CostBucketKey, float],
        *,
        cost_type: CostType,
        project_currency: str | None,
    ) -> float:
        return self._make_cost_policy_engine()._sum_bucket_for_type(
            values, cost_type=cost_type, project_currency=project_currency
        )

    def _sum_bucket_excluding_type(
        self,
        values: dict[CostBucketKey, float],
        *,
        excluded_type: CostType,
        project_currency: str | None,
    ) -> float:
        return self._make_cost_policy_engine()._sum_bucket_excluding_type(
            values, excluded_type=excluded_type, project_currency=project_currency
        )
