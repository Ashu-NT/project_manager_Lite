from __future__ import annotations

from datetime import date
from typing import Any

from core.interfaces import CostRepository, ProjectResourceRepository, ResourceRepository
from core.models import CostType, Project
from core.services.finance.helpers import normalize_currency, resolve_rate
from core.services.finance.models import FinanceLedgerRow
from core.services.reporting import ReportingService


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
) -> list[FinanceLedgerRow]:
    rows: list[FinanceLedgerRow] = []
    project_currency = normalize_currency(getattr(project, "currency", None), None)
    anchor = project.start_date or as_of
    for pr in project_resource_repo.list_by_project(project.id):
        if not getattr(pr, "is_active", True):
            continue
        planned_hours = float(getattr(pr, "planned_hours", 0.0) or 0.0)
        if planned_hours <= 0.0:
            continue
        resource_id = str(getattr(pr, "resource_id", "") or "")
        resource = resource_cache.get(resource_id)
        if resource_id and resource_id not in resource_cache:
            resource = resource_repo.get(resource_id)
            resource_cache[resource_id] = resource
        rate = resolve_rate(
            pr_rate=getattr(pr, "hourly_rate", None),
            resource_rate=(None if resource is None else getattr(resource, "hourly_rate", None)),
        )
        if rate <= 0.0:
            continue
        currency = normalize_currency(
            getattr(pr, "currency_code", None)
            or (None if resource is None else getattr(resource, "currency_code", None)),
            project_currency,
        )
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
    reporting_service: ReportingService,
    project: Project,
    task_map: dict[str, object],
    as_of: date,
) -> list[FinanceLedgerRow]:
    rows: list[FinanceLedgerRow] = []
    for resource_row in reporting_service.get_project_labor_details(project.id):
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
