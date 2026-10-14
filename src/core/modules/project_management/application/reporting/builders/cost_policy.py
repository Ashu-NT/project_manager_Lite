"""Reporting cost policy -- the single financial authority shared by builders.

Business logic lives in financials/cost/engines (CostPolicyEngine,
LaborCostEngine). This policy object wires the scoped fact readers into those
engines once, so every report builder composes finance facts the same way.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.core.modules.project_management.application.financials.cost.engines.cost_policy_engine import (
    CostControlTotals,
    CostPolicyComposition,
    CostPolicyEngine,
    CostPolicySnapshot,
)
from src.core.modules.project_management.application.financials.cost.engines.labor_cost import (
    LaborCostEngine,
)
from src.core.modules.project_management.contracts.reads.financials import (
    EvmSeriesFacts,
    EvmSeriesReader,
    FinanceSnapshotFacts,
    FinanceSnapshotReader,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import NotFoundError

CostBucketKey = tuple[CostType, str]


class ReportingCostPolicy:
    """Composes scoped finance/EVM facts through the canonical engines."""

    def __init__(
        self,
        *,
        rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
        finance_snapshot_reader: FinanceSnapshotReader,
        evm_series_reader: EvmSeriesReader,
    ) -> None:
        self._rate_resolver = rate_resolver
        self._tenant_context_service = tenant_context_service
        self._finance_snapshot_reader = finance_snapshot_reader
        self._evm_series_reader = evm_series_reader

    def build_cost_policy_snapshot(
        self,
        project_id: str,
        *,
        as_of: date | None = None,
    ) -> CostPolicySnapshot:
        return self.compose_finance_policy(
            project_id, as_of=as_of or date.today()  # noqa: DTZ011
        )[1].snapshot

    def compose_finance_policy(
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

    def read_evm_facts(
        self,
        project_id: str,
        *,
        baseline_id: str | None,
        as_of: date,
    ) -> EvmSeriesFacts:
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
        return facts

    def sum_bucket_map(
        self,
        values: dict[CostBucketKey, Decimal],
        project_currency: str | None,
    ) -> Decimal:
        return CostPolicyEngine.for_facts(
            rate_resolver=self._rate_resolver,
            tenant_context_service=self._tenant_context_service,
        )._sum_bucket_map(values, project_currency)


__all__ = [
    "CostBucketKey",
    "CostControlTotals",
    "CostPolicySnapshot",
    "ReportingCostPolicy",
]
