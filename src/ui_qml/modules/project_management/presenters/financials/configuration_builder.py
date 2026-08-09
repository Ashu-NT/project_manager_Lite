from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.configuration import (
    FinancialConfigurationRecordDto,
    FinancialConfigurationWorkspaceDto,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _record(item: FinancialConfigurationRecordDto) -> FinancialsRecordViewModel:
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


def build_finance_configuration_views(
    source: FinancialConfigurationWorkspaceDto,
) -> dict[str, object]:
    profile = source.profile
    return {
        "profile": FinancialsDetailViewModel(
            id=profile.project_id,
            title=profile.title,
            status_label=profile.status_label,
            subtitle=profile.subtitle,
            empty_state=(
                "Select a project to review its financial profile."
                if not profile.project_id
                else "The project financial profile is not configured."
            ),
            fields=tuple(
                FinancialsDetailFieldViewModel(
                    label=field.label,
                    value=field.value,
                    supporting_text=field.supporting_text,
                )
                for field in profile.fields
            ),
        ),
        "budget_versions": FinancialsCollectionViewModel(
            title="Budget Versions",
            subtitle="Governed budget revisions and approval state.",
            empty_state="No budget version exists for this project.",
            items=tuple(_record(item) for item in source.budget_versions),
        ),
        "budget_lines": FinancialsCollectionViewModel(
            title="Budget Lines",
            subtitle="Authorized amounts by cost code and WBS task.",
            empty_state="No budget lines exist for this project.",
            items=tuple(_record(item) for item in source.budget_lines),
            page=source.budget_line_page,
            page_size=source.budget_line_page_size,
            total=source.budget_line_total,
        ),
        "rate_cards": FinancialsCollectionViewModel(
            title="Rate Cards",
            subtitle="Project and organization rate sources visible to this project.",
            empty_state="No rate cards are visible to this project.",
            items=tuple(_record(item) for item in source.rate_cards),
        ),
        "rate_lines": FinancialsCollectionViewModel(
            title="Rate Lines",
            subtitle="Effective cost and billing rate definitions.",
            empty_state="No rate lines exist on the visible cards.",
            items=tuple(_record(item) for item in source.rate_lines),
            page=source.rate_line_page,
            page_size=source.rate_line_page_size,
            total=source.rate_line_total,
        ),
        "planned_cost_versions": FinancialsCollectionViewModel(
            title="Planned Cost Snapshots",
            subtitle="Versioned assignment-based labor calculations.",
            empty_state="No planned-cost snapshot has been calculated.",
            items=tuple(_record(item) for item in source.planned_cost_versions),
        ),
        "planned_cost_lines": FinancialsCollectionViewModel(
            title="Planned Cost Lines",
            subtitle="Calculated labor cost by task, resource, and cost code.",
            empty_state="No planned-cost lines exist for this project.",
            items=tuple(_record(item) for item in source.planned_cost_lines),
            page=source.planned_cost_line_page,
            page_size=source.planned_cost_line_page_size,
            total=source.planned_cost_line_total,
        ),
    }


__all__ = ["build_finance_configuration_views"]
