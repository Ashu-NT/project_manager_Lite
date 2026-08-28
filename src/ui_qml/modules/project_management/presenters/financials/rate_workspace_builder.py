from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.rates import (
    FinancialRateTableRecordDto,
    FinancialRateWorkspaceDto,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _record(item: FinancialRateTableRecordDto) -> FinancialsRecordViewModel:
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


def build_rate_workspace_views(source: FinancialRateWorkspaceDto) -> dict[str, object]:
    detail = source.selected_rate_card
    return {
        "selected_rate_card_id": source.selected_rate_card_id,
        "selected_rate_card": FinancialsDetailViewModel(
            id=detail.id,
            title=detail.title,
            status_label=detail.status_label,
            subtitle=detail.subtitle,
            empty_state="Select a Rate Card to inspect its authoritative lines.",
            fields=tuple(
                FinancialsDetailFieldViewModel(label, value, supporting)
                for label, value, supporting in detail.fields
            ),
        ),
        "rate_cards": FinancialsCollectionViewModel(
            title="Rate Cards",
            subtitle="Organization fallback and project override cards visible to this project.",
            empty_state="No Rate Cards match the current filters.",
            items=tuple(_record(item) for item in source.cards),
            page=source.card_page,
            page_size=source.card_page_size,
            total=source.card_total,
        ),
        "rate_lines": FinancialsCollectionViewModel(
            title="Selected Rate Card Lines",
            subtitle="Effective-dated financial rates; historical postings use immutable snapshots.",
            empty_state=(
                "Select a Rate Card."
                if not source.selected_rate_card_id
                else "No Rate Card Lines match the current filters."
            ),
            items=tuple(_record(item) for item in source.lines),
            page=source.line_page,
            page_size=source.line_page_size,
            total=source.line_total,
        ),
        "rate_card_sort_key": source.card_sort_key,
        "rate_card_sort_direction": source.card_sort_direction,
        "rate_line_sort_key": source.line_sort_key,
        "rate_line_sort_direction": source.line_sort_direction,
        "rate_card_search": source.card_search,
        "rate_card_scope": source.card_scope,
        "rate_card_status": source.card_status,
        "rate_line_search": source.line_search,
        "rate_line_rate_type": source.line_rate_type,
        "rate_line_status": source.line_status,
        "rate_line_effective_status": source.line_effective_status,
    }


__all__ = ["build_rate_workspace_views"]
