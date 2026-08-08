from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceLedgerRow,
    LaborDetailsResult,
)
from src.core.modules.project_management.application.financials.utils.helpers import (
    normalize_currency,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    FinanceSnapshotFacts,
)
from src.core.modules.project_management.domain.enums import CostType


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
    *, item: object, task: object | None, project: object, as_of: date
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
    *, task: object | None, project: object, as_of: date
) -> date:
    if task is not None:
        for candidate in ("actual_end", "end_date", "actual_start", "start_date"):
            value = getattr(task, candidate, None)
            if isinstance(value, date):
                return value
    start_date = getattr(project, "start_date", None)
    return start_date if isinstance(start_date, date) else as_of


def build_cost_item_ledger_rows(
    *, facts: FinanceSnapshotFacts, manual_included: dict[str, bool]
) -> list[FinanceLedgerRow]:
    rows: list[FinanceLedgerRow] = []
    project = facts.project
    task_map = {task.task_id: task for task in facts.tasks}
    project_currency = normalize_currency(project.currency, None)
    for item in facts.cost_items:
        task = task_map.get(item.task_id) if item.task_id else None
        try:
            cost_type = CostType(item.cost_type)
        except ValueError:
            cost_type = CostType.OTHER
        currency = normalize_currency(item.currency_code, project_currency)
        is_labor_adjustment = cost_type == CostType.LABOR
        source_key = "LABOR_ADJUSTMENT" if is_labor_adjustment else "DIRECT_COST"
        source_label = "Labor Adjustment" if is_labor_adjustment else "Direct Cost"
        anchor = resolve_item_anchor_date(
            item=item,
            task=task,
            project=project,
            as_of=facts.as_of,
        )
        for stage in ("planned", "committed", "actual"):
            amount = read_stage_amount(item=item, stage=stage, as_of=facts.as_of)
            if amount <= 0.0:
                continue
            included = bool(manual_included.get(stage, False)) if is_labor_adjustment else True
            rows.append(
                FinanceLedgerRow(
                    project_id=facts.project_id,
                    source_key=source_key,
                    source_label=source_label,
                    cost_type=cost_type.value,
                    stage=stage,
                    amount=amount,
                    currency=currency,
                    occurred_on=anchor,
                    reference_type="cost_item",
                    reference_id=item.cost_item_id,
                    reference_label=item.description or "Cost item",
                    task_id=item.task_id,
                    task_name=(None if task is None else task.name),
                    resource_id=None,
                    resource_name=None,
                    included_in_policy=included,
                )
            )
    return rows


def build_computed_labor_plan_rows(
    *, facts: FinanceSnapshotFacts, labor_details: LaborDetailsResult
) -> list[FinanceLedgerRow]:
    project_currency = normalize_currency(facts.project.currency, None)
    anchor = facts.project.start_date or facts.as_of
    return [
        FinanceLedgerRow(
            project_id=facts.project_id,
            source_key="COMPUTED_LABOR",
            source_label="Computed Labor",
            cost_type=CostType.LABOR.value,
            stage="planned",
            amount=float(row.total_cost),
            currency=normalize_currency(row.currency_code, project_currency),
            occurred_on=anchor,
            reference_type="project_resource",
            reference_id=row.project_resource_id,
            reference_label=row.resource_name or row.resource_id or "Project resource",
            task_id=None,
            task_name=None,
            resource_id=row.resource_id or None,
            resource_name=row.resource_name or None,
            included_in_policy=True,
        )
        for row in labor_details.planned_rows
    ]


def build_computed_labor_actual_rows(
    *, facts: FinanceSnapshotFacts, labor_details: LaborDetailsResult
) -> list[FinanceLedgerRow]:
    rows: list[FinanceLedgerRow] = []
    task_map = {task.task_id: task for task in facts.tasks}
    for resource_row in labor_details.rows:
        for assignment in resource_row.assignments:
            if assignment.cost <= 0.0:
                continue
            task = task_map.get(assignment.task_id)
            rows.append(
                FinanceLedgerRow(
                    project_id=facts.project_id,
                    source_key="COMPUTED_LABOR",
                    source_label="Computed Labor",
                    cost_type=CostType.LABOR.value,
                    stage="actual",
                    amount=float(assignment.cost),
                    currency=assignment.currency_code or resource_row.currency_code,
                    occurred_on=resolve_assignment_anchor_date(
                        task=task,
                        project=facts.project,
                        as_of=facts.as_of,
                    ),
                    reference_type="assignment",
                    reference_id=assignment.assignment_id,
                    reference_label=assignment.task_name or "Assignment",
                    task_id=assignment.task_id or None,
                    task_name=(None if task is None else task.name),
                    resource_id=resource_row.resource_id or None,
                    resource_name=resource_row.resource_name or None,
                    included_in_policy=True,
                )
            )
    return rows


__all__ = [
    "build_computed_labor_actual_rows",
    "build_computed_labor_plan_rows",
    "build_cost_item_ledger_rows",
]
