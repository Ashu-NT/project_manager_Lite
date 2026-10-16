from __future__ import annotations

from datetime import date, datetime

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.contracts.reads.financials.forecasts.models.forecast_facts import (
    FinanceForecastWorkspaceFacts,
    ForecastLineFact,
    ForecastVersionFact,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _label(value: object) -> str:
    return str(value or "").replace("_", " ").strip().title()


def _date_label(value: date | None) -> str:
    return value.isoformat() if value else "Not set"


def _datetime_label(value: datetime | None) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else "Not set"


def build_forecast_workspace_views(
    source: FinanceForecastWorkspaceFacts,
    *,
    version_search: str = "",
    version_status: str = "",
    generation_mode: str = "",
    line_search: str = "",
    line_source_type: str = "",
) -> dict[str, object]:
    selected = source.selected_forecast
    detail = (
        FinancialsDetailViewModel(
            empty_state="Select a Forecast Version to inspect authoritative ETC.",
            id=selected.id,
            title=f"Forecast r{selected.revision} - {selected.name}",
            status_label=_label(selected.status),
            subtitle=(
                f"As of {selected.as_of_date.isoformat()} | "
                f"{_label(selected.generation_mode)}"
            ),
            fields=tuple(
                FinancialsDetailFieldViewModel(*field)
                for field in (
                    (
                        "Authoritative ETC",
                        format_money(selected.total_etc, selected.currency_code),
                        "",
                    ),
                    ("Currency", selected.currency_code, "No FX conversion applied"),
                    (
                        "Line count",
                        str(selected.line_count),
                        "Independent of the visible page",
                    ),
                    (
                        "Submitted",
                        _datetime_label(selected.submitted_at),
                        selected.submitted_by or "",
                    ),
                    (
                        "Approved",
                        _datetime_label(selected.approved_at),
                        selected.approved_by or "",
                    ),
                    ("Row version", str(selected.row_version), ""),
                )
            ),
            state={
                "rowVersion": selected.row_version,
                "status": selected.status,
                "revision": selected.revision,
                "currency": selected.currency_code,
                "asOf": selected.as_of_date.isoformat(),
                "approvalRequestId": selected.approval_request_id or "",
                "canSubmit": selected.can_submit,
                "canRequestApproval": selected.can_request_approval,
                "canApprove": selected.can_approve,
                "canReject": selected.can_reject,
            },
        )
        if selected is not None
        else FinancialsDetailViewModel(
            empty_state="Select a Forecast Version to inspect authoritative ETC."
        )
    )
    return {
        "selected_forecast_id": source.selected_forecast_id,
        "selected_forecast": detail,
        "forecast_versions": FinancialsCollectionViewModel(
            title="Forecast Versions",
            subtitle="Governed ETC versions for the selected project.",
            empty_state="No forecast versions match the current filters.",
            items=tuple(_version_record(item) for item in source.versions.items),
            page=source.versions.page,
            page_size=source.versions.page_size,
            total=source.versions.total,
        ),
        "forecast_lines": FinancialsCollectionViewModel(
            title="Selected Forecast Lines",
            subtitle="Authoritative ETC sources; totals are independent of this page.",
            empty_state=(
                "Select a Forecast Version."
                if not source.selected_forecast_id
                else "No lines match the current filters."
            ),
            items=tuple(_line_record(item) for item in source.lines.items),
            page=source.lines.page,
            page_size=source.lines.page_size,
            total=source.lines.total,
        ),
        "forecast_version_sort_key": source.versions.sort_key,
        "forecast_version_sort_direction": source.versions.sort_direction,
        "forecast_line_sort_key": source.lines.sort_key,
        "forecast_line_sort_direction": source.lines.sort_direction,
        "forecast_version_search": version_search,
        "forecast_version_status": version_status,
        "forecast_generation_mode": generation_mode,
        "forecast_line_search": line_search,
        "forecast_line_source_type": line_source_type,
        "show_generate_forecast": source.show_generate,
        "can_generate_forecast": source.can_generate,
        "generate_forecast_disabled_reason": source.generate_disabled_reason,
    }


def _version_record(item: ForecastVersionFact) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        can_primary_action=False,
        can_secondary_action=False,
        id=item.id,
        title=f"r{item.revision} - {item.name}",
        status_label=_label(item.status),
        subtitle=f"As of {_date_label(item.as_of_date)} | {_label(item.generation_mode)}",
        supporting_text=(
            f"{format_money(item.total_etc, item.currency_code)} | "
            f"{item.line_count} line{'s' if item.line_count != 1 else ''}"
        ),
        meta_text=(
            f"Approved {_datetime_label(item.approved_at)}"
            if item.approved_at
            else f"Row version {item.row_version}"
        ),
        state={
            "revision": item.revision,
            "status": item.status,
            "generationMode": item.generation_mode,
            "currency": item.currency_code,
            "asOf": item.as_of_date.isoformat(),
            "totalEtc": str(item.total_etc),
            "lineCount": item.line_count,
            "rowVersion": item.row_version,
            "approvalRequestId": item.approval_request_id or "",
            "canSubmit": item.can_submit,
            "canRequestApproval": item.can_request_approval,
            "canApprove": item.can_approve,
            "canReject": item.can_reject,
        },
    )


def _line_record(item: ForecastLineFact) -> FinancialsRecordViewModel:
    reference = " / ".join(
        part for part in (item.source_reference_type, item.source_reference_id) if part
    )
    period = (
        f"{_date_label(item.period_start)} to {_date_label(item.period_end)}"
        if item.period_start and item.period_end
        else "Unphased"
    )
    return FinancialsRecordViewModel(
        can_primary_action=False,
        can_secondary_action=False,
        id=item.id,
        title=item.description or f"{_label(item.source_type)} forecast line",
        status_label=_label(item.source_kind),
        subtitle=(
            f"{item.cost_code} | {item.task_name}"
            if item.task_name != "Unassigned"
            else item.cost_code
        ),
        supporting_text=(
            f"{format_money(item.amount, item.currency_code)} | "
            f"{_label(item.source_type)}"
        ),
        meta_text=" | ".join(part for part in (period, reference) if part),
        state={
            "forecastId": item.forecast_id,
            "costCode": item.cost_code,
            "costCodeName": item.cost_code_name,
            "taskName": item.task_name,
            "wbsCode": item.wbs_code,
            "sourceKind": item.source_kind,
            "sourceType": item.source_type,
            "sourceReferenceType": item.source_reference_type,
            "sourceReferenceId": item.source_reference_id,
            "sourceSnapshotAt": (
                item.source_snapshot_at.isoformat() if item.source_snapshot_at else ""
            ),
            "amount": str(item.amount),
            "currency": item.currency_code,
            "rowVersion": item.row_version,
        },
    )


__all__ = ["build_forecast_workspace_views"]
