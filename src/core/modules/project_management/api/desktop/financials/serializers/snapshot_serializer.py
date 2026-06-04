"""Finance snapshot serializer."""

from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.snapshots import (
    FinancialLedgerRowDto,
    FinancialPeriodRowDto,
    FinancialSnapshotDto,
)
from src.core.modules.project_management.api.desktop.financials.serializers.analytics_serializer import serialize_analytics
from src.core.modules.project_management.api.desktop.financials.formatters.money_formatter import format_money
from src.core.modules.project_management.api.desktop.financials.formatters.date_formatter import format_date
from src.core.modules.project_management.api.desktop.financials.formatters.enum_formatter import format_enum_label


def serialize_snapshot(project_id: str, snapshot) -> FinancialSnapshotDto:
    currency = (snapshot.project_currency or "").strip().upper() or None
    return FinancialSnapshotDto(
        project_id=project_id,
        project_currency=currency,
        budget=float(snapshot.budget or 0.0),
        budget_label=format_money(snapshot.budget, currency),
        planned=float(snapshot.planned or 0.0),
        planned_label=format_money(snapshot.planned, currency),
        committed=float(snapshot.committed or 0.0),
        committed_label=format_money(snapshot.committed, currency),
        actual=float(snapshot.actual or 0.0),
        actual_label=format_money(snapshot.actual, currency),
        exposure=float(snapshot.exposure or 0.0),
        exposure_label=format_money(snapshot.exposure, currency),
        available=(None if snapshot.available is None else float(snapshot.available)),
        available_label="Open" if snapshot.available is None else format_money(snapshot.available, currency),
        ledger=tuple(
            FinancialLedgerRowDto(
                source_label=row.source_label,
                stage=format_enum_label(row.stage),
                amount=float(row.amount or 0.0),
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
                planned=float(row.planned or 0.0),
                planned_label=format_money(row.planned, currency),
                committed=float(row.committed or 0.0),
                committed_label=format_money(row.committed, currency),
                actual=float(row.actual or 0.0),
                actual_label=format_money(row.actual, currency),
                forecast=float(row.forecast or 0.0),
                forecast_label=format_money(row.forecast, currency),
                exposure=float(row.exposure or 0.0),
                exposure_label=format_money(row.exposure, currency),
            )
            for row in snapshot.cashflow
        ),
        by_source=serialize_analytics(snapshot.by_source, currency),
        by_cost_type=serialize_analytics(snapshot.by_cost_type, currency),
        by_resource=serialize_analytics(snapshot.by_resource, currency),
        by_task=serialize_analytics(snapshot.by_task, currency),
        notes=tuple(snapshot.notes or ()),
    )


def empty_snapshot(*, project_id: str, notes: tuple[str, ...] = ()) -> FinancialSnapshotDto:
    return FinancialSnapshotDto(
        project_id=project_id, project_currency=None,
        budget=0.0, budget_label="0.00",
        planned=0.0, planned_label="0.00",
        committed=0.0, committed_label="0.00",
        actual=0.0, actual_label="0.00",
        exposure=0.0, exposure_label="0.00",
        available=None, available_label="Open",
        ledger=(), cashflow=(), by_source=(), by_cost_type=(), by_resource=(), by_task=(),
        notes=notes,
    )


__all__ = ["empty_snapshot", "serialize_snapshot"]
