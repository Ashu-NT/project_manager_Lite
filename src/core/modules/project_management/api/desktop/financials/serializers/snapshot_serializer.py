"""Finance snapshot serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.snapshots import (
    FinancialLedgerRowDto,
    FinancialPeriodRowDto,
    FinancialSnapshotDto,
)
from src.core.modules.project_management.api.desktop.financials.serializers.analytics_serializer import serialize_analytics
from src.core.modules.project_management.api.desktop.common.financial_formatting import format_money
from src.core.modules.project_management.api.desktop.financials.formatters.date_formatter import format_date
from src.core.modules.project_management.api.desktop.financials.formatters.enum_formatter import format_enum_label
from src.core.platform.finance.money import canonical_decimal_text


def serialize_snapshot(project_id: str, snapshot) -> FinancialSnapshotDto:
    currency = (snapshot.project_currency or "").strip().upper() or None
    return FinancialSnapshotDto(
        project_id=project_id,
        project_currency=currency,
        budget=canonical_decimal_text(snapshot.budget),
        budget_label=format_money(snapshot.budget, currency),
        planned=canonical_decimal_text(snapshot.planned),
        planned_label=format_money(snapshot.planned, currency),
        committed=canonical_decimal_text(snapshot.committed),
        committed_label=format_money(snapshot.committed, currency),
        actual=canonical_decimal_text(snapshot.actual),
        actual_label=format_money(snapshot.actual, currency),
        exposure=canonical_decimal_text(snapshot.exposure),
        exposure_label=format_money(snapshot.exposure, currency),
        available=(None if snapshot.available is None else canonical_decimal_text(snapshot.available)),
        available_label="Open" if snapshot.available is None else format_money(snapshot.available, currency),
        ledger=tuple(
            FinancialLedgerRowDto(
                source_label=row.source_label,
                stage=format_enum_label(row.stage),
                amount=canonical_decimal_text(row.amount),
                amount_label=format_money(row.amount, row.currency or currency),
                reference_label=row.reference_label,
                task_name=row.task_name or "Not linked to a task",
                resource_name=row.resource_name or "No resource",
                occurred_on=row.occurred_on,
                occurred_on_label=format_date(row.occurred_on),
                included_in_policy=bool(row.included_in_policy),
            )
            for row in snapshot.ledger
        ),
        cashflow=tuple(
            FinancialPeriodRowDto(
                period_key=row.period_key,
                planned=canonical_decimal_text(row.planned),
                planned_label=format_money(row.planned, currency),
                committed=canonical_decimal_text(row.committed),
                committed_label=format_money(row.committed, currency),
                actual=canonical_decimal_text(row.actual),
                actual_label=format_money(row.actual, currency),
                forecast=canonical_decimal_text(row.forecast),
                forecast_label=format_money(row.forecast, currency),
                exposure=canonical_decimal_text(row.exposure),
                exposure_label=format_money(row.exposure, currency),
            )
            for row in snapshot.cashflow
        ),
        by_source=serialize_analytics(snapshot.by_source, currency),
        by_cost_type=serialize_analytics(snapshot.by_cost_type, currency),
        by_resource=serialize_analytics(snapshot.by_resource, currency),
        by_task=serialize_analytics(snapshot.by_task, currency),
        notes=tuple(snapshot.notes or ()),
        labor_rates_complete=not getattr(snapshot, "unresolved_labor_rates", ()),
        unresolved_labor_rate_count=len(getattr(snapshot, "unresolved_labor_rates", ()) or ()),
        forecast_etc=(
            None if snapshot.forecast_etc is None else canonical_decimal_text(snapshot.forecast_etc)
        ),
        forecast_etc_label=(
            "Not approved"
            if snapshot.forecast_etc is None
            else format_money(snapshot.forecast_etc, currency)
        ),
        estimate_at_completion=(
            None
            if snapshot.estimate_at_completion is None
            else canonical_decimal_text(snapshot.estimate_at_completion)
        ),
        estimate_at_completion_label=(
            "Not available"
            if snapshot.estimate_at_completion is None
            else format_money(snapshot.estimate_at_completion, currency)
        ),
        variance_at_completion=(
            None
            if snapshot.variance_at_completion is None
            else canonical_decimal_text(snapshot.variance_at_completion)
        ),
        variance_at_completion_label=(
            "Not available"
            if snapshot.variance_at_completion is None
            else format_money(snapshot.variance_at_completion, currency)
        ),
        as_of=snapshot.as_of,
        approved_budget_id=snapshot.approved_budget_id or "",
        approved_budget_revision=snapshot.approved_budget_revision,
        approved_forecast_id=snapshot.approved_forecast_id or "",
        approved_forecast_revision=snapshot.approved_forecast_revision,
        approved_forecast_as_of=snapshot.approved_forecast_as_of,
    )


def empty_snapshot(*, project_id: str, notes: tuple[str, ...] = ()) -> FinancialSnapshotDto:
    return FinancialSnapshotDto(
        project_id=project_id, project_currency=None,
        budget="0", budget_label="0.00",
        planned="0", planned_label="0.00",
        committed="0", committed_label="0.00",
        actual="0", actual_label="0.00",
        exposure="0", exposure_label="0.00",
        available=None, available_label="Open",
        ledger=(), cashflow=(), by_source=(), by_cost_type=(), by_resource=(), by_task=(),
        notes=notes,
    )


__all__ = ["empty_snapshot", "serialize_snapshot"]
