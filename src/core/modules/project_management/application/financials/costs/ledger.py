from __future__ import annotations

from datetime import date

from src.core.modules.project_management.contracts.repositories.project import ProjectResourceRepository
from src.core.modules.project_management.contracts.repositories.resource import ResourceRepository
from src.core.modules.project_management.contracts.repositories.cost import CostRepository
from src.core.modules.project_management.contracts.repositories.rate_resolution import (
    LaborRateResolver,
)
from src.core.modules.project_management.domain.enums import CostType
from src.core.modules.project_management.domain.financials.rate_cards import RateType
from src.core.modules.project_management.domain.projects.project import Project
from src.core.modules.project_management.application.financials.utils.helpers import (
    normalize_currency,
)
from src.core.modules.project_management.application.financials.models.finance_models import FinanceLedgerRow


def read_stage_amount(*, item: object, stage: str, as_of: date) -> float:
    if stage == "planned":
        return float(getattr(item, "planned_amount", 0.0) or 0.0)
    if stage == "committed":
        return float(getattr(item, "committed_amount", 0.0) or 0.0)
    if stage != "actual":
        return 0.0
    incurred = getattr(item, "incurred_date", None)
    if incurred is not None and incurred > as_of:
        return 0.0
    return float(getattr(item, "actual_amount", 0.0) or 0.0)


def resolve_item_anchor_date(
    *,
    item: object,
    task: object | None,
    project: Project,
    as_of: date,
) -> date:
    incurred = getattr(item, "incurred_date", None)
    if isinstance(incurred, date):
        return incurred
    if task is not None:
        for candidate in ("actual_end", "end_date", "actual_start", "start_date"):
            value = getattr(task, candidate, None)
            if isinstance(value, date):
                return value
    for candidate in ("start_date", "end_date"):
        value = getattr(project, candidate, None)
        if isinstance(value, date):
            return value
    return as_of


def resolve_assignment_anchor_date(
    *,
    task: object | None,
    project: Project,
    as_of: date,
) -> date:
    if task is not None:
        for candidate in ("actual_end", "end_date", "actual_start", "start_date"):
            value = getattr(task, candidate, None)
            if isinstance(value, date):
                return value
    if isinstance(getattr(project, "start_date", None), date):
        return project.start_date
    return as_of


def build_cost_item_ledger_rows(
    *,
    cost_repo: CostRepository,
    project: Project,
    task_map: dict[str, object],
    as_of: date,
    manual_included: dict[str, bool],
) -> list[FinanceLedgerRow]:
    rows: list[FinanceLedgerRow] = []
    project_currency = normalize_currency(getattr(project, "currency", None), None)
    for item in cost_repo.list_by_project(project.id):
        task_id = getattr(item, "task_id", None)
        task = task_map.get(task_id) if task_id else None
        cost_type = getattr(item, "cost_type", None) or CostType.OTHER
        cost_type_value = cost_type.value if hasattr(cost_type, "value") else str(cost_type)
        currency = normalize_currency(getattr(item, "currency_code", None), project_currency)
        is_labor_adjustment = cost_type == CostType.LABOR
        source_key = "LABOR_ADJUSTMENT" if is_labor_adjustment else "DIRECT_COST"
        source_label = "Labor Adjustment" if is_labor_adjustment else "Direct Cost"
        anchor_date = resolve_item_anchor_date(item=item, task=task, project=project, as_of=as_of)

        for stage in ("planned", "committed", "actual"):
            amount = read_stage_amount(item=item, stage=stage, as_of=as_of)
            if amount <= 0.0:
                continue
            included = bool(manual_included.get(stage, False)) if is_labor_adjustment else True
            rows.append(
                FinanceLedgerRow(
                    project_id=project.id,
                    source_key=source_key,
                    source_label=source_label,
                    cost_type=cost_type_value,
                    stage=stage,
                    amount=float(amount),
                    currency=currency,
                    occurred_on=anchor_date,
                    reference_type="cost_item",
                    reference_id=str(getattr(item, "id", "")),
                    reference_label=str(getattr(item, "description", "") or "Cost item"),
                    task_id=task_id,
                    task_name=(None if task is None else str(getattr(task, "name", "") or "")),
                    resource_id=None,
                    resource_name=None,
                    included_in_policy=included,
                )
            )
    return rows


def build_computed_labor_plan_rows(
    *,
    project_resource_repo: ProjectResourceRepository,
    resource_repo: ResourceRepository,
    project: Project,
    as_of: date,
    resource_cache: dict[str, object | None],
    rate_resolver: LaborRateResolver,
    tenant_id: str,
    organization_id: str,
) -> list[FinanceLedgerRow]:
    rows: list[FinanceLedgerRow] = []
    project_currency = normalize_currency(getattr(project, "currency", None), None)
    anchor = project.start_date or as_of

    active_prs = [
        pr
        for pr in project_resource_repo.list_by_project(project.id)
        if getattr(pr, "is_active", True)
        and float(getattr(pr, "planned_hours", 0.0) or 0.0) > 0.0
        and getattr(pr, "resource_id", None)
    ]
    resource_ids = tuple({str(pr.resource_id) for pr in active_prs})
    # Same rate-card resolution CostPolicyEngine uses for its own planned-
    # labor total — a second resolve_many call (not a shared cache), but the
    # same source of truth, so this ledger's rows never disagree with the
    # engine's totals in the same finance snapshot.
    batch = (
        rate_resolver.resolve_many(
            tenant_id=tenant_id,
            organization_id=organization_id,
            project_id=project.id,
            resource_ids=resource_ids,
            rate_type=RateType.COST,
            as_of=as_of,
            unit="HOUR",
        )
        if resource_ids
        else None
    )

    for pr in active_prs:
        planned_hours = float(getattr(pr, "planned_hours", 0.0) or 0.0)
        resource_id = str(getattr(pr, "resource_id", "") or "")
        resource = resource_cache.get(resource_id)
        if resource_id and resource_id not in resource_cache:
            resource = resource_repo.get(resource_id)
            resource_cache[resource_id] = resource

        snapshot = batch.snapshot_for(resource_id) if batch is not None else None
        if snapshot is None:
            continue  # unresolved — excluded from this ledger, not zeroed in
        rate = float(snapshot.monetary_rate.money.amount)
        currency = normalize_currency(snapshot.monetary_rate.money.currency.code, project_currency)
        amount = planned_hours * rate
        rows.append(
            FinanceLedgerRow(
                project_id=project.id,
                source_key="COMPUTED_LABOR",
                source_label="Computed Labor",
                cost_type=CostType.LABOR.value,
                stage="planned",
                amount=float(amount),
                currency=currency,
                occurred_on=anchor,
                reference_type="project_resource",
                reference_id=str(getattr(pr, "id", "")),
                reference_label=(getattr(resource, "name", None) if resource is not None else resource_id)
                or "Project resource",
                task_id=None,
                task_name=None,
                resource_id=(resource_id or None),
                resource_name=(None if resource is None else str(getattr(resource, "name", "") or "")),
                included_in_policy=True,
            )
        )
    return rows


def build_computed_labor_actual_rows(
    *,
    labor_provider: object,
    project: Project,
    task_map: dict[str, object],
    as_of: date,
) -> list[FinanceLedgerRow]:
    """Build actual labor ledger rows from a labor provider.

    labor_provider must expose get_project_labor_details(project_id, as_of) —
    works with both LaborCostEngine and ReportingService (duck-typed).
    """
    rows: list[FinanceLedgerRow] = []
    for resource_row in labor_provider.get_project_labor_details(project.id, as_of):
        resource_id = str(getattr(resource_row, "resource_id", "") or "")
        resource_name = str(getattr(resource_row, "resource_name", "") or "")
        for assignment in getattr(resource_row, "assignments", []):
            amount = float(getattr(assignment, "cost", 0.0) or 0.0)
            if amount <= 0.0:
                continue
            task_id = str(getattr(assignment, "task_id", "") or "")
            task = task_map.get(task_id)
            anchor = resolve_assignment_anchor_date(task=task, project=project, as_of=as_of)
            rows.append(
                FinanceLedgerRow(
                    project_id=project.id,
                    source_key="COMPUTED_LABOR",
                    source_label="Computed Labor",
                    cost_type=CostType.LABOR.value,
                    stage="actual",
                    amount=float(amount),
                    currency=(getattr(assignment, "currency_code", None) or getattr(resource_row, "currency_code", None)),
                    occurred_on=anchor,
                    reference_type="assignment",
                    reference_id=str(getattr(assignment, "assignment_id", "")),
                    reference_label=str(getattr(assignment, "task_name", "") or "Assignment"),
                    task_id=(task_id or None),
                    task_name=(None if task is None else str(getattr(task, "name", "") or "")),
                    resource_id=(resource_id or None),
                    resource_name=(resource_name or None),
                    included_in_policy=True,
                )
            )
    return rows


__all__ = [
    "build_cost_item_ledger_rows",
    "build_computed_labor_plan_rows",
    "build_computed_labor_actual_rows",
]
