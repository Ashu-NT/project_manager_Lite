"""Labor cost engine — owns all labor cost calculation logic.

Computes labor details (actual, from assignments) and, as diagnostics on the
same result, unpriced resource-envelope planning rows. Reporting delegates
here; this class is the authoritative source for labor figures.

Labor rates are resolved through the ADR-PF-005 rate-card system
(``LaborRateResolver.resolve_many``), batched once per calculation rather
than per assignment/resource — ``ProjectResource.hourly_rate``/
``Resource.hourly_rate`` are no longer read directly here.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from src.core.platform.common.exceptions import BusinessRuleError, NotFoundError
from src.core.modules.project_management.contracts.repositories.projects.project import (
    ProjectRepository,
    ProjectResourceRepository,
)
from src.core.modules.project_management.contracts.repositories.tasks.task import (
    AssignmentRepository,
    TaskRepository,
)
from src.core.modules.project_management.contracts.repositories.resources.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.finance.configuration.financial_configuration import ProjectFinancialProfileRepository
from src.core.modules.project_management.contracts.repositories.finance.rate_cards.rate_resolution import (
    LaborRateResolver,
    RateResolutionBatch,
    UnresolvedLaborRate,
)
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.domain.tasks.task import TaskAssignment
from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService

from src.core.modules.project_management.application.financials.models.finance_models import (
    LaborAssignmentRow,
    LaborDetailsResult,
    LaborResourceRow,
    PlannedLaborResourceRow,
)

if TYPE_CHECKING:
    from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
        FinanceSnapshotFacts,
    )


class LaborCostEngine:
    """
    Compute labor cost details for a project.

    Uses assignment execution data (hours_logged x resolved rate) for actuals,
    and ProjectResource planning data (planned_hours x resolved rate) for the
    planned-envelope diagnostic rows carried alongside them. Both rates come
    from the same batched rate-card resolution per calculation — never a
    per-assignment/per-resource call.
    """

    def __init__(
        self,
        *,
        project_repo: ProjectRepository,
        task_repo: TaskRepository,
        assignment_repo: AssignmentRepository,
        resource_repo: ResourceRepository,
        project_resource_repo: ProjectResourceRepository,
        rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
        financial_profile_repo: ProjectFinancialProfileRepository | None = None,
    ) -> None:
        self._project_repo = project_repo
        self._task_repo = task_repo
        self._assignment_repo = assignment_repo
        self._resource_repo = resource_repo
        self._project_resource_repo = project_resource_repo
        self._rate_resolver = rate_resolver
        self._tenant_context_service = tenant_context_service
        self._financial_profile_repo = financial_profile_repo

    @classmethod
    def for_facts(
        cls,
        *,
        rate_resolver: LaborRateResolver,
        tenant_context_service: TenantContextService,
    ) -> "LaborCostEngine":
        """Build the engine for immutable Reader facts without repository fallbacks."""
        return cls(
            project_repo=None,  # type: ignore[arg-type]
            task_repo=None,  # type: ignore[arg-type]
            assignment_repo=None,  # type: ignore[arg-type]
            resource_repo=None,  # type: ignore[arg-type]
            project_resource_repo=None,  # type: ignore[arg-type]
            rate_resolver=rate_resolver,
            tenant_context_service=tenant_context_service,
        )

    def _resolve_scope(self, project) -> tuple[str, str]:
        context = self._tenant_context_service.require_organization_context(
            operation_label="resolve project labor rates"
        )
        if project.organization_id and project.organization_id != context.organization_id:
            raise BusinessRuleError(
                "Project does not belong to the active organization.",
                code="PROJECT_ORGANIZATION_MISMATCH",
            )
        assert context.organization_id is not None  # guaranteed by require_organization_context
        return context.tenant_id, context.organization_id

    def calculate_project_labor_details(
        self,
        project_id: str,
        as_of: date,
        *,
        facts: FinanceSnapshotFacts | None = None,
    ) -> LaborDetailsResult:
        """Rich result — rows plus every resource whose rate could not be
        resolved as of ``as_of``. ``get_project_labor_details`` is a thin
        wrapper returning ``list(result.rows)``."""
        if facts is not None:
            return self._calculate_from_finance_facts(project_id, as_of=as_of, facts=facts)

        if self._project_repo is None:
            raise BusinessRuleError(
                "LaborCostEngine was configured for Reader facts only.",
                code="LABOR_FACTS_REQUIRED",
            )

        project = self._project_repo.get(project_id)
        if not project:
            raise NotFoundError("Project not found.", code="PROJECT_NOT_FOUND")
        tenant_id, organization_id = self._resolve_scope(project)

        tasks = self._task_repo.list_by_project(project_id)
        task_map = {t.id: t for t in tasks}
        task_ids = list(task_map.keys())
        if not task_ids:
            return LaborDetailsResult(rows=(), unresolved_rates=())

        assignments = self._assignment_repo.list_by_tasks(task_ids)

        by_res: dict[str, list[TaskAssignment]] = {}
        for a in assignments:
            by_res.setdefault(a.resource_id, []).append(a)

        resource_ids = tuple(by_res.keys())
        batch = self._rate_resolver.resolve_many(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project_id,
            resource_ids=resource_ids,
            rate_type=RateType.COST,
            as_of=as_of,
            unit="HOUR",
        )

        resources_by_id = {r.id: r for r in self._resource_repo.list_by_ids(list(resource_ids))}

        result: list[LaborResourceRow] = []
        for res_id, assigns in by_res.items():
            snapshot = batch.snapshot_for(res_id)
            if snapshot is None:
                # Unresolved — excluded from rows/totals, not zeroed in;
                # recorded once in batch.unresolved below.
                continue
            res = resources_by_id.get(res_id)
            res_name = res.name if res else "<unknown>"
            hourly_rate = float(snapshot.monetary_rate.money.amount)
            currency = snapshot.monetary_rate.money.currency.code
            total_hours = 0.0
            total_cost = 0.0
            as_rows: list[LaborAssignmentRow] = []
            for a in assigns:
                hours = float(getattr(a, "hours_logged", 0.0) or 0.0)
                task_name = task_map.get(a.task_id).name if a.task_id in task_map else "<unknown>"
                cost = hours * hourly_rate
                total_hours += hours
                total_cost += cost
                as_rows.append(
                    LaborAssignmentRow(
                        assignment_id=a.id,
                        task_id=a.task_id,
                        task_name=task_name,
                        hours=hours,
                        hourly_rate=hourly_rate,
                        currency_code=currency,
                        cost=cost,
                    )
                )
            result.append(
                LaborResourceRow(
                    resource_id=res_id,
                    resource_name=res_name,
                    total_hours=total_hours,
                    hourly_rate=hourly_rate,
                    currency_code=currency,
                    total_cost=total_cost,
                    assignments=as_rows,
                )
            )

        result.sort(key=lambda r: r.total_cost, reverse=True)
        return LaborDetailsResult(rows=tuple(result), unresolved_rates=batch.unresolved)

    def _calculate_from_finance_facts(
        self,
        project_id: str,
        *,
        as_of: date,
        facts: FinanceSnapshotFacts,
        rate_batch: RateResolutionBatch | None = None,
    ) -> LaborDetailsResult:
        """Calculate planned and actual labor from one scoped reader result."""
        if facts.project_id != project_id or (
            rate_batch is None and facts.as_of != as_of
        ):
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
            hourly_rate = float(snapshot.monetary_rate.money.amount)
            currency = snapshot.monetary_rate.money.currency.code
            assignment_rows: list[LaborAssignmentRow] = []
            total_hours = 0.0
            total_cost = 0.0
            for assignment in assignments:
                hours = float(assignment.hours_logged or 0.0)
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
            hourly_rate = float(snapshot.monetary_rate.money.amount)
            planned_rows.append(
                PlannedLaborResourceRow(
                    project_resource_id=plan.project_resource_id,
                    resource_id=plan.resource_id,
                    resource_name=(resource.name if resource is not None else plan.resource_id),
                    planned_hours=float(plan.planned_hours),
                    hourly_rate=hourly_rate,
                    currency_code=snapshot.monetary_rate.money.currency.code,
                    total_cost=float(plan.planned_hours) * hourly_rate,
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

    def calculate_project_labor_series(
        self,
        project_id: str,
        *,
        as_of_dates: tuple[date, ...],
        facts: FinanceSnapshotFacts,
    ) -> tuple[tuple[date, LaborDetailsResult], ...]:
        """Evaluate prepared labor facts for several dates with one source read."""
        if facts.project_id != project_id:
            raise BusinessRuleError(
                "Finance labor facts do not match the requested project.",
                code="FINANCE_FACT_SCOPE_MISMATCH",
            )
        dates = tuple(dict.fromkeys(as_of_dates))
        if not dates:
            return ()
        resource_ids = self._finance_fact_resource_ids(facts)
        if not resource_ids:
            empty = LaborDetailsResult(rows=(), unresolved_rates=())
            return tuple((as_of, empty) for as_of in dates)
        batches = self._rate_resolver.resolve_many_dates(
            tenant_id=facts.tenant_id,
            organization_id=facts.organization_id,
            project_id=project_id,
            resource_ids=resource_ids,
            rate_type=RateType.COST,
            as_of_dates=dates,
            unit="HOUR",
        )
        return tuple(
            (
                dated.as_of,
                self._calculate_from_finance_facts(
                    project_id,
                    as_of=dated.as_of,
                    facts=facts,
                    rate_batch=dated.batch,
                ),
            )
            for dated in batches
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

    def get_project_labor_details(self, project_id: str, as_of: date) -> list[LaborResourceRow]:
        """Return labor cost details grouped by resource for the given project."""
        return list(self.calculate_project_labor_details(project_id, as_of).rows)

    def get_unresolved_labor_rates(
        self, project_id: str, as_of: date
    ) -> tuple[UnresolvedLaborRate, ...]:
        return self.calculate_project_labor_details(project_id, as_of).unresolved_rates


__all__ = ["LaborCostEngine"]
