"""Baseline variance record serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.baseline_variance import (
    BaselineVarianceRecordDto,
    FinancialBaselineVersionDto,
)
from src.core.modules.project_management.api.desktop.common.financial_formatting import format_signed_money
from src.core.platform.finance.money import canonical_decimal_text


def serialize_variance_record(r) -> BaselineVarianceRecordDto:
    cost_var = r.cost_variance
    return BaselineVarianceRecordDto(
        task_id=str(r.task_id or ""),
        task_name=str(r.task_name or r.task_id or "Task"),
        start_variance_days=int(r.start_variance_days or 0),
        finish_variance_days=int(r.finish_variance_days or 0),
        cost_variance=canonical_decimal_text(cost_var),
        cost_variance_label=format_signed_money(cost_var),
        tone="danger" if cost_var > 0 else "success" if cost_var < 0 else "default",
    )


def serialize_baseline_version(value) -> FinancialBaselineVersionDto:
    status = str(getattr(getattr(value, "status", ""), "value", getattr(value, "status", "")))
    return FinancialBaselineVersionDto(
        id=str(value.id),
        name=str(value.name),
        status=status,
        status_label=status.replace("_", " ").title(),
        version=int(value.version),
        created_at_label=str(value.created_at or ""),
        approved_at_label=str(value.approved_at or ""),
    )


__all__ = ["serialize_baseline_version", "serialize_variance_record"]
