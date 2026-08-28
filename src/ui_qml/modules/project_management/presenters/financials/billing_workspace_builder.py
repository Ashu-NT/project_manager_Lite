from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.billing_workspace import (
    FinancialBillingDetailDto,
    FinancialBillingReadWorkspaceDto,
    FinancialBillingTableRecordDto,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _record(item: FinancialBillingTableRecordDto) -> FinancialsRecordViewModel:
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


def _detail(item: FinancialBillingDetailDto, *, empty_state: str) -> FinancialsDetailViewModel:
    return FinancialsDetailViewModel(
        id=item.id,
        title=item.title,
        status_label=item.status_label,
        subtitle=item.subtitle,
        description=item.description,
        empty_state=empty_state,
        fields=tuple(
            FinancialsDetailFieldViewModel(label, value, supporting)
            for label, value, supporting in item.fields
        ),
        state=dict(item.state),
    )


def build_billing_workspace_views(source: FinancialBillingReadWorkspaceDto) -> dict[str, object]:
    return {
        "billing_profile": _detail(source.profile, empty_state="No Billing Profile exists for this Project."),
        "selected_billing_preparation_id": source.selected_preparation_id,
        "selected_billing_preparation": _detail(
            source.selected_preparation,
            empty_state="Select a Billing Preparation to inspect governance and Accounting outcome evidence.",
        ),
        "billing_schedule": FinancialsCollectionViewModel(
            title="Billing Schedule",
            subtitle="PM-owned commercial schedule evidence and source-consumption state.",
            empty_state="No Billing Schedule lines match the current filters.",
            items=tuple(_record(item) for item in source.schedule),
            page=source.schedule_page,
            page_size=source.schedule_page_size,
            total=source.schedule_total,
        ),
        "billing_preparations": FinancialsCollectionViewModel(
            title="Billing Preparations",
            subtitle="Governed PM commercial handoff packages; not Accounting invoices.",
            empty_state="No Billing Preparations match the current filters.",
            items=tuple(_record(item) for item in source.preparations),
            page=source.preparation_page,
            page_size=source.preparation_page_size,
            total=source.preparation_total,
        ),
        "billing_preparation_lines": FinancialsCollectionViewModel(
            title="Selected Preparation Lines",
            subtitle="Immutable source, rate, markup, and currency snapshots.",
            empty_state=(
                "Select a Billing Preparation."
                if not source.selected_preparation_id
                else "No Preparation Lines match the current filters."
            ),
            items=tuple(_record(item) for item in source.lines),
            page=source.line_page,
            page_size=source.line_page_size,
            total=source.line_total,
        ),
        "billing_schedule_sort_key": source.schedule_sort_key,
        "billing_schedule_sort_direction": source.schedule_sort_direction,
        "billing_preparation_sort_key": source.preparation_sort_key,
        "billing_preparation_sort_direction": source.preparation_sort_direction,
        "billing_line_sort_key": source.line_sort_key,
        "billing_line_sort_direction": source.line_sort_direction,
        "billing_schedule_search": source.schedule_search,
        "billing_schedule_status": source.schedule_status,
        "billing_schedule_source_state": source.schedule_source_state,
        "billing_preparation_search": source.preparation_search,
        "billing_preparation_status": source.preparation_status,
        "billing_preparation_method": source.preparation_method,
        "billing_preparation_approval_status": source.preparation_approval_status,
        "billing_preparation_delivery_state": source.preparation_delivery_state,
        "billing_preparation_correction_state": source.preparation_correction_state,
        "billing_line_search": source.line_search,
        "billing_line_source_type": source.line_source_type,
        "billing_line_source_state": source.line_source_state,
    }


__all__ = ["build_billing_workspace_views"]
