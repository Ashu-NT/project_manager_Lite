"""Labor cost engine — owns all labor cost calculation logic. Reporting delegates here;
this class is the authoritative source for labor figures."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from src.core.modules.project_management.application.financials.models.finance_models import (
    LaborAssignmentRow,
    LaborDetailsResult,
    LaborResourceRow,
    PlannedLaborResourceRow,
)
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
    RateResolutionBatch,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError

if TYPE_CHECKING:
    from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
        FinanceSnapshotFacts,
    )


class LaborCostEngine:
    """Computes labor cost details for a project: actuals from assignment execution data
    (hours_logged x resolved rate), and diagnostic planned-envelope rows (planned_hours x
    resolved rate) alongside them. Both rates come from one batched rate-card resolution per
    calculation -- ``ProjectResource.hourly_rate``/``Resource.hourly_rate`` are never read
    directly here."""

    def __init__(
        self, *, rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
    ) -> None:
        self._rate_resolver = rate_resolver
        self._tenant_context_service = tenant_context_service

    @classmethod
    def for_facts(
        cls, *, rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
    ) -> LaborCostEngine:
        return cls(
            rate_resolver=rate_resolver,
            tenant_context_service=tenant_context_service,
        )

    def calculate_project_labor_details(
        self, project_id: str, as_of: date, *, facts: FinanceSnapshotFacts,
    ) -> LaborDetailsResult:
        """Price operational diagnostics, never posted Actual Cost authority."""
        return self._calculate_from_finance_facts(project_id, as_of=as_of, facts=facts)

    def _calculate_from_finance_facts(
        self,
        project_id: str,
        *,
        as_of: date,
        facts: FinanceSnapshotFacts,
        rate_batch: RateResolutionBatch | None = None,
    ) -> LaborDetailsResult:
        """Calculate planned and actual labor from one scoped reader result."""
        if facts.project_id != project_id or facts.as_of != as_of:
            raise BusinessRuleError(
                "Finance labor facts do not match the requested snapshot.",
                code="FINANCE_FACT_SCOPE_MISMATCH",
            )

        tasks = {row.task_id: row for row in facts.tasks}
        resources = {row.resource_id: row for row in facts.resources}
        by_resource: dict[str, list[object]] = {}
        for assignment in facts.assignments:
            by_resource.setdefault(assignment.resource_id, []).append(assignment)

        active_plans = tuple(
            row
            for row in facts.project_resources
            if row.is_active and row.planned_hours > 0.0 and row.resource_id
        )
        planned_resource_ids = {row.resource_id for row in active_plans}
        actual_resource_ids = set(by_resource)
        resource_ids = self._finance_fact_resource_ids(facts)
        if not resource_ids:
            return LaborDetailsResult(rows=(), unresolved_rates=())

        batch = rate_batch
        if batch is None:
            batch = self._rate_resolver.resolve_many(
                tenant_id=facts.tenant_id,
                organization_id=facts.organization_id,
                project_id=project_id,
                resource_ids=resource_ids,
                rate_type=RateType.COST,
                as_of=as_of,
                unit="HOUR",
            )

        actual_rows: list[LaborResourceRow] = []
        for resource_id, assignments in by_resource.items():
            snapshot = batch.snapshot_for(resource_id)
            if snapshot is None:
                continue
            resource = resources.get(resource_id)
            hourly_rate = snapshot.monetary_rate.money.amount
            currency = snapshot.monetary_rate.money.currency.code
            assignment_rows: list[LaborAssignmentRow] = []
            total_hours = Decimal(0)
            total_cost = Decimal(0)
            for assignment in assignments:
                hours = Decimal(str(assignment.hours_logged))
                cost = hours * hourly_rate
                task = tasks.get(assignment.task_id)
                total_hours += hours
                total_cost += cost
                assignment_rows.append(
                    LaborAssignmentRow(
                        assignment_id=assignment.assignment_id,
                        task_id=assignment.task_id,
                        task_name=(task.name if task is not None else "<unknown>"),
                        hours=hours,
                        hourly_rate=hourly_rate,
                        currency_code=currency,
                        cost=cost,
                    )
                )
            actual_rows.append(
                LaborResourceRow(
                    resource_id=resource_id,
                    resource_name=(resource.name if resource is not None else "<unknown>"),
                    total_hours=total_hours,
                    hourly_rate=hourly_rate,
                    currency_code=currency,
                    total_cost=total_cost,
                    assignments=assignment_rows,
                )
            )

        planned_rows: list[PlannedLaborResourceRow] = []
        for plan in active_plans:
            snapshot = batch.snapshot_for(plan.resource_id)
            if snapshot is None:
                continue
            resource = resources.get(plan.resource_id)
            hourly_rate = snapshot.monetary_rate.money.amount
            planned_rows.append(
                PlannedLaborResourceRow(
                    project_resource_id=plan.project_resource_id,
                    resource_id=plan.resource_id,
                    resource_name=(resource.name if resource is not None else plan.resource_id),
                    planned_hours=Decimal(str(plan.planned_hours)),
                    hourly_rate=hourly_rate,
                    currency_code=snapshot.monetary_rate.money.currency.code,
                    total_cost=Decimal(str(plan.planned_hours)) * hourly_rate,
                )
            )

        actual_rows.sort(key=lambda row: row.total_cost, reverse=True)
        unresolved_actual = tuple(
            row for row in batch.unresolved if row.resource_id in actual_resource_ids
        )
        unresolved_planned = tuple(
            row for row in batch.unresolved if row.resource_id in planned_resource_ids
        )
        return LaborDetailsResult(
            rows=tuple(actual_rows),
            unresolved_rates=unresolved_actual,
            planned_rows=tuple(planned_rows),
            planned_unresolved_rates=unresolved_planned,
        )

    @staticmethod
    def _finance_fact_resource_ids(facts: FinanceSnapshotFacts) -> tuple[str, ...]:
        planned = {
            row.resource_id
            for row in facts.project_resources
            if row.is_active and row.planned_hours > 0.0 and row.resource_id
        }
        assigned = {row.resource_id for row in facts.assignments if row.resource_id}
        return tuple(sorted(planned | assigned))



__all__ = ["LaborCostEngine"]
