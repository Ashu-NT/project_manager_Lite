from __future__ import annotations

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.api.desktop.financials.models.lifecycle import (
    FinancialBaselineVersionDto,
    FinancialChangeDto,
    FinancialChangeImpactDto,
    FinancialForecastLineDto,
    FinancialForecastVersionDto,
)


def _label(value: object) -> str:
    raw = str(getattr(value, "value", value) or "")
    return raw.replace("_", " ").strip().title()


def _date_label(value: object) -> str:
    if value is None:
        return ""
    isoformat = getattr(value, "isoformat", None)
    return str(isoformat() if callable(isoformat) else value)


def _version_label(identifier: str | None, revision: int | None) -> str:
    if not identifier:
        return "Not established"
    return f"r{revision} | {identifier}" if revision is not None else str(identifier)


def serialize_forecast_version(value) -> FinancialForecastVersionDto:
    return FinancialForecastVersionDto(
        id=value.id,
        name=value.name,
        status=value.status.value,
        status_label=_label(value.status),
        revision=value.revision,
        row_version=value.row_version,
        currency_code=value.currency_code,
        as_of_label=_date_label(value.as_of_date),
        generation_mode_label=_label(value.generation_mode),
        approved_at_label=_date_label(value.approved_at),
        notes=value.notes,
    )


def serialize_forecast_line(value) -> FinancialForecastLineDto:
    period_parts = tuple(
        part for part in (_date_label(value.period_start), _date_label(value.period_end)) if part
    )
    reference_parts = tuple(
        part for part in (value.source_reference_type, value.source_reference_id) if part
    )
    return FinancialForecastLineDto(
        id=value.id,
        description=value.description,
        amount_label=format_money(value.amount, value.currency_code),
        source_kind_label=_label(value.source_kind),
        source_type_label=_label(value.source_type),
        cost_code_id=value.cost_code_id,
        task_id=value.task_id or "",
        source_reference_label=" / ".join(reference_parts),
        source_snapshot_label=_date_label(value.source_snapshot_at),
        period_label=" to ".join(period_parts),
    )


def serialize_financial_change(value) -> FinancialChangeDto:
    return FinancialChangeDto(
        id=value.id,
        title=value.title,
        status=value.status.value,
        status_label=_label(value.status),
        revision=value.revision,
        effective_date_label=_date_label(value.effective_date),
        reason=value.reason,
        description=value.description,
        base_budget_label=_version_label(value.base_budget_id, value.base_budget_revision),
        base_forecast_label=_version_label(value.base_forecast_id, value.base_forecast_revision),
        applied_budget_id=value.applied_budget_id or "",
        applied_forecast_id=value.applied_forecast_id or "",
        applied_schedule_count=value.applied_schedule_count,
        applied_at_label=_date_label(value.applied_at),
    )


def serialize_financial_change_impact(value) -> FinancialChangeImpactDto:
    target_parts = tuple(
        part
        for part in (
            value.target_line_id,
            f"task v{value.target_task_version}" if value.target_task_version else "",
        )
        if part
    )
    schedule_parts = tuple(
        part for part in (_date_label(value.schedule_start), _date_label(value.schedule_finish)) if part
    )
    applied_parts = tuple(
        part for part in (value.applied_reference_type, value.applied_reference_id) if part
    )
    return FinancialChangeImpactDto(
        id=value.id,
        impact_type_label=_label(value.impact_type),
        description=value.description,
        amount_label=(
            format_money(value.amount, value.currency_code)
            if value.currency_code is not None
            else "Not monetary"
        ),
        cost_code_id=value.cost_code_id or "",
        task_id=value.task_id or "",
        target_label=" | ".join(target_parts),
        schedule_label=" to ".join(schedule_parts),
        applied_reference_label=" / ".join(applied_parts),
    )


def serialize_baseline_version(value) -> FinancialBaselineVersionDto:
    return FinancialBaselineVersionDto(
        id=value.id,
        name=value.name,
        status=value.status.value,
        status_label=_label(value.status),
        version=value.version,
        created_at_label=_date_label(value.created_at),
        approved_at_label=_date_label(value.approved_at),
    )


__all__ = [
    "serialize_baseline_version",
    "serialize_financial_change",
    "serialize_financial_change_impact",
    "serialize_forecast_line",
    "serialize_forecast_version",
]
