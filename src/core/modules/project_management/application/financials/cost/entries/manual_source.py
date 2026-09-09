from __future__ import annotations

from datetime import date

from src.core.modules.project_management.contracts.financial_sources.reference import (
    FinancialPostingPurpose,
    FinancialSourceModule,
    FinancialSourceReference,
    FinancialSourceType,
    financial_source_content_hash,
)
from src.core.modules.project_management.domain.financials.cost_entry import (
    ProjectCostEntryKind,
)
from src.core.platform.finance import Money, MoneyPayload


def build_manual_content(
    *,
    description: str,
    kind: ProjectCostEntryKind,
    money: Money,
    transaction_date: date,
    cost_code_id: str,
    task_id: str | None,
    resource_id: str | None,
) -> dict[str, object]:
    return {
        "description": str(description or "").strip(),
        "entry_kind": kind.value,
        "amount": MoneyPayload.from_domain(money).amount,
        "currency_code": money.currency.code,
        "transaction_date": transaction_date.isoformat(),
        "cost_code_id": str(cost_code_id or "").strip(),
        "task_id": str(task_id or "").strip() or None,
        "resource_id": str(resource_id or "").strip() or None,
    }


def build_manual_source(
    *,
    tenant_id: str,
    organization_id: str,
    project_id: str,
    command_id: str,
    content: dict[str, object],
) -> FinancialSourceReference:
    return FinancialSourceReference(
        tenant_id=tenant_id,
        organization_id=organization_id,
        project_id=project_id,
        source_module=FinancialSourceModule.PROJECT_MANAGEMENT,
        source_type=FinancialSourceType.MANUAL_COMMAND,
        source_id=command_id,
        source_revision="1",
        content_hash=financial_source_content_hash(content),
        posting_purpose=FinancialPostingPurpose.MANUAL_ACTUAL,
    )


__all__ = ["build_manual_content", "build_manual_source"]
