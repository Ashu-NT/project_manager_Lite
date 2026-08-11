"""Shared finance export projection used by every report format."""

from __future__ import annotations

from decimal import Decimal

from src.core.modules.project_management.infrastructure.reporting.models.contexts import (
    ReportExportContext,
)


def finance_metadata_rows(ctx: ReportExportContext) -> tuple[tuple[str, object], ...]:
    snapshot = ctx.finance_snapshot
    page = ctx.finance_ledger_page
    if snapshot is None or page is None:
        return ()
    budget_version = _version_label(
        snapshot.approved_budget_id,
        snapshot.approved_budget_revision,
    )
    forecast_version = _version_label(
        snapshot.approved_forecast_id,
        snapshot.approved_forecast_revision,
    )
    page_start = page.offset + 1 if page.rows else 0
    page_end = page.offset + len(page.rows)
    return (
        ("Generated at (UTC)", ctx.generated_at.isoformat()),
        ("Snapshot as of", snapshot.as_of.isoformat()),
        (
            "Currency basis",
            f"{snapshot.currency_basis}: {snapshot.project_currency or 'Not configured'}",
        ),
        ("Period grouping", snapshot.period_granularity),
        ("Approved budget version", budget_version),
        ("Approved forecast version", forecast_version),
        (
            "Approved forecast as of",
            snapshot.approved_forecast_as_of.isoformat()
            if snapshot.approved_forecast_as_of
            else "Not approved",
        ),
        (
            "Sensitive labor detail",
            "Included" if snapshot.sensitive_detail_included else "Redacted",
        ),
        ("Ledger page", f"Rows {page_start}-{page_end} of {page.total}"),
        ("Ledger page limit", page.limit),
        ("More ledger rows available", "Yes" if page.has_more else "No"),
    )


def finance_summary_rows(ctx: ReportExportContext) -> tuple[tuple[str, Decimal | None], ...]:
    snapshot = ctx.finance_snapshot
    if snapshot is None:
        return ()
    return (
        ("Approved budget", snapshot.budget),
        ("Planned cost", snapshot.planned),
        ("Open commitments", snapshot.committed),
        ("Posted actual", snapshot.actual),
        ("Approved forecast ETC", snapshot.forecast_etc),
        ("Estimate at completion", snapshot.estimate_at_completion),
        ("Variance at completion", snapshot.variance_at_completion),
        ("Current exposure", snapshot.exposure),
        ("Available after actuals and commitments", snapshot.available),
    )


def finance_reconciliation_rows(
    ctx: ReportExportContext,
) -> tuple[tuple[str, Decimal | None, Decimal | None, Decimal | None], ...]:
    snapshot = ctx.finance_snapshot
    if snapshot is None:
        return ()
    reconciliation = snapshot.reconciliation
    return (
        (
            "Posted actual",
            reconciliation.posted_actual_control,
            reconciliation.posted_actual_ledger,
            reconciliation.posted_actual_delta,
        ),
        (
            "Open commitments",
            reconciliation.open_commitment_control,
            reconciliation.open_commitment_ledger,
            reconciliation.open_commitment_delta,
        ),
        (
            "Approved forecast ETC",
            reconciliation.forecast_etc_control,
            reconciliation.forecast_etc_ledger,
            reconciliation.forecast_etc_delta,
        ),
    )


def finance_ledger_headers() -> tuple[str, ...]:
    return (
        "Date",
        "Period Start",
        "Period End",
        "Source",
        "Source Type",
        "Stage",
        "Cost Type",
        "Cost Code ID",
        "Financial Period ID",
        "Reference Type",
        "Reference ID",
        "Reference",
        "Task ID",
        "Task",
        "Resource ID",
        "Resource",
        "Amount",
        "Currency",
    )


def finance_ledger_values(row) -> tuple[object, ...]:
    return (
        row.occurred_on.isoformat() if row.occurred_on else "",
        row.period_start.isoformat() if row.period_start else "",
        row.period_end.isoformat() if row.period_end else "",
        row.source_label,
        row.source_type or "",
        row.stage,
        row.cost_type,
        row.cost_code_id or "",
        row.financial_period_id or "",
        row.reference_type,
        row.reference_id,
        row.reference_label,
        row.task_id or "",
        row.task_name or "",
        row.resource_id or "",
        row.resource_name or "",
        row.amount,
        row.currency or "",
    )


def _version_label(identifier: str | None, revision: int | None) -> str:
    if identifier is None:
        return "Not approved"
    revision_label = "?" if revision is None else str(revision)
    return f"{identifier} / revision {revision_label}"


__all__ = [
    "finance_ledger_headers",
    "finance_ledger_values",
    "finance_metadata_rows",
    "finance_reconciliation_rows",
    "finance_summary_rows",
]
