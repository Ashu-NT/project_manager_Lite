from __future__ import annotations

from src.core.modules.project_management.application.financials.models.finance_models import (
    FinanceLedgerRow,
)
from src.core.modules.project_management.application.financials.utils.helpers import (
    normalize_currency,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_snapshot_facts import (
    FinanceSnapshotFacts,
)


def build_finance_ledger_rows(*, facts: FinanceSnapshotFacts) -> list[FinanceLedgerRow]:
    """Project canonical financial facts into the shared reporting ledger."""

    project_currency = normalize_currency(facts.project.currency_code, None)
    task_map = {task.task_id: task for task in facts.tasks}
    resource_map = {resource.resource_id: resource for resource in facts.resources}
    rows: list[FinanceLedgerRow] = []
    for fact in facts.ledger_entries:
        task = task_map.get(fact.task_id or "")
        resource = resource_map.get(fact.resource_id or "")
        rows.append(
            FinanceLedgerRow(
                project_id=facts.project_id,
                source_key=fact.source_key,
                source_label=fact.source_label,
                cost_type=fact.cost_type,
                stage=fact.stage,
                amount=fact.amount,
                currency=normalize_currency(fact.currency_code, project_currency),
                occurred_on=fact.occurred_on,
                reference_type=fact.reference_type,
                reference_id=fact.fact_id,
                reference_label=fact.description,
                task_id=fact.task_id,
                task_name=None if task is None else task.name,
                resource_id=fact.resource_id,
                resource_name=None if resource is None else resource.name,
                included_in_policy=True,
            )
        )
    return rows


__all__ = ["build_finance_ledger_rows"]
