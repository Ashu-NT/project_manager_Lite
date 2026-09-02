from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.forecasts import (
    FinancialForecastWorkspaceDto,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _record(item) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        id=item.id,
        title=item.title,
        status_label=item.status_label,
        subtitle=item.subtitle,
        supporting_text=item.supporting_text,
        meta_text=item.meta_text,
        can_primary_action=False,
        can_secondary_action=False,
        state=dict(item.state),
    )


def build_forecast_workspace_views(
    source: FinancialForecastWorkspaceDto,
) -> dict[str, object]:
    detail = source.selected_forecast
    return {
        "selected_forecast_id": source.selected_forecast_id,
        "selected_forecast": FinancialsDetailViewModel(
            id=detail.id,
            title=detail.title,
            status_label=detail.status_label,
            subtitle=detail.subtitle,
            empty_state="Select a Forecast Version to inspect authoritative ETC.",
            fields=tuple(
                FinancialsDetailFieldViewModel(label, value, supporting)
                for label, value, supporting in detail.fields
            ),
            state=dict(detail.state),
        ),
        "forecast_versions": FinancialsCollectionViewModel(
            title="Forecast Versions",
            subtitle="Governed ETC versions for the selected project.",
            empty_state="No forecast versions match the current filters.",
            items=tuple(_record(item) for item in source.versions),
            page=source.version_page,
            page_size=source.version_page_size,
            total=source.version_total,
        ),
        "forecast_lines": FinancialsCollectionViewModel(
            title="Selected Forecast Lines",
            subtitle="Authoritative ETC sources; totals are independent of this page.",
            empty_state=(
                "Select a Forecast Version."
                if not source.selected_forecast_id
                else "No lines match the current filters."
            ),
            items=tuple(_record(item) for item in source.lines),
            page=source.line_page,
            page_size=source.line_page_size,
            total=source.line_total,
        ),
        "forecast_version_sort_key": source.version_sort_key,
        "forecast_version_sort_direction": source.version_sort_direction,
        "forecast_line_sort_key": source.line_sort_key,
        "forecast_line_sort_direction": source.line_sort_direction,
        "forecast_version_search": source.version_search,
        "forecast_version_status": source.version_status,
        "forecast_generation_mode": source.generation_mode,
        "forecast_line_search": source.line_search,
        "forecast_line_source_type": source.line_source_type,
        "show_generate_forecast": source.show_generate,
        "can_generate_forecast": source.can_generate,
        "generate_forecast_disabled_reason": source.generate_disabled_reason,
    }


__all__ = ["build_forecast_workspace_views"]
