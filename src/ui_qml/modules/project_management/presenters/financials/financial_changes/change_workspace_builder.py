from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.changes import (
    FinancialChangeTableRecordDto,
    FinancialChangeWorkspaceDto,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _record(item: FinancialChangeTableRecordDto) -> FinancialsRecordViewModel:
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


def build_change_workspace_views(source: FinancialChangeWorkspaceDto) -> dict[str, object]:
    detail = source.selected_change
    return {
        "selected_change_id": source.selected_change_id,
        "selected_change": FinancialsDetailViewModel(
            id=detail.id,
            title=detail.title,
            status_label=detail.status_label,
            subtitle=detail.subtitle,
            description=detail.description,
            empty_state="Select a Change Request to inspect its governance and impacts.",
            fields=tuple(
                FinancialsDetailFieldViewModel(label, value, supporting)
                for label, value, supporting in detail.fields
            ),
            state=dict(detail.state),
        ),
        "financial_changes": FinancialsCollectionViewModel(
            title="Change Requests",
            subtitle="Governed requests with snapshotted Finance bases.",
            empty_state="No Change Requests match the current filters.",
            items=tuple(_record(item) for item in source.changes),
            page=source.change_page,
            page_size=source.change_page_size,
            total=source.change_total,
        ),
        "financial_change_impacts": FinancialsCollectionViewModel(
            title="Selected Change Impacts",
            subtitle="Typed Budget, Forecast, and Schedule evidence.",
            empty_state=(
                "Select a Change Request."
                if not source.selected_change_id
                else "No impacts match the current filters."
            ),
            items=tuple(_record(item) for item in source.impacts),
            page=source.impact_page,
            page_size=source.impact_page_size,
            total=source.impact_total,
        ),
        "change_sort_key": source.change_sort_key,
        "change_sort_direction": source.change_sort_direction,
        "impact_sort_key": source.impact_sort_key,
        "impact_sort_direction": source.impact_sort_direction,
        "change_search": source.change_search,
        "change_status": source.change_status,
        "change_approval_status": source.change_approval_status,
        "change_applied_state": source.change_applied_state,
        "impact_search": source.impact_search,
        "impact_type": source.impact_type,
        "impact_applied_state": source.impact_applied_state,
        "can_create_change": source.can_create,
    }


__all__ = ["build_change_workspace_views"]
