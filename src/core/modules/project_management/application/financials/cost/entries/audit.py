from __future__ import annotations

import json

from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntry,
)
from src.core.platform.finance import MoneyPayload
from src.core.shared.audit import record_audit_entry


def record_project_cost_entry_audit(
    owner: object,
    *,
    operation: str,
    entry: ProjectCostEntry,
    actor_id: str | None = None,
    actor_type: str = "user",
    actor_username: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    payload = {
        "status": entry.status.value,
        "entry_kind": entry.entry_kind.value,
        "amount": MoneyPayload.from_domain(entry.money).amount,
        "currency_code": entry.currency_code,
        "base_amount": (
            MoneyPayload.from_domain(entry.base_money).amount
            if entry.base_money is not None
            else None
        ),
        "base_currency_code": entry.base_currency_code,
        "transaction_date": entry.transaction_date.isoformat(),
        "posting_date": entry.posting_date.isoformat() if entry.posting_date else None,
        "financial_period_id": entry.financial_period_id,
        "cost_code_id": entry.cost_code_id,
        "task_id": entry.task_id,
        "resource_id": entry.resource_id,
        "source_module": entry.source_module.value,
        "source_type": entry.source_type.value,
        "source_id": entry.source_id,
        "source_revision": entry.source_revision,
        "reverses_entry_id": entry.reverses_entry_id,
        "reversed_by_entry_id": entry.reversed_by_entry_id,
        "row_version": entry.row_version,
    }
    record_audit_entry(
        owner,
        operation=f"project_cost_entry.{operation}",
        entity_type="project_cost_entry",
        entity_id=entry.id,
        entity_parent_id=entry.project_id,
        module="project_management",
        actor_id=actor_id,
        actor_type=actor_type,
        actor_username=actor_username,
        old_value=None,
        new_value=json.dumps(payload, sort_keys=True),
        workspace_id=entry.project_id,
        request_id=request_id,
        source="application",
        severity="high",
        compliance_tag="financial",
        metadata={"action": operation, **(metadata or {})},
        commit=False,
        fail_closed=True,
    )


__all__ = ["record_project_cost_entry_audit"]
