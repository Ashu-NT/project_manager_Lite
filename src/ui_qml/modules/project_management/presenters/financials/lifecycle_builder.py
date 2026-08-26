from __future__ import annotations

from src.core.modules.project_management.api.desktop import (
    ProjectManagementFinancialsDesktopApi,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    BaselineVarianceRowViewModel,
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def _selected_id(items, requested_id: str | None, *, preferred_status: str = "") -> str:
    if requested_id and any(item.id == requested_id for item in items):
        return requested_id
    preferred = next(
        (item for item in items if getattr(item, "status", "") == preferred_status),
        None,
    )
    return preferred.id if preferred is not None else (items[0].id if items else "")


def build_lifecycle_views(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    project_id: str,
    selected_forecast_id: str | None,
    selected_change_id: str | None,
    selected_baseline_id: str | None,
) -> dict[str, object]:
    return {
        **build_forecast_lifecycle_views(
            desktop_api,
            project_id=project_id,
            selected_forecast_id=selected_forecast_id,
        ),
        **build_change_lifecycle_views(
            desktop_api,
            project_id=project_id,
            selected_change_id=selected_change_id,
        ),
        **build_variance_views(
            desktop_api,
            project_id=project_id,
            selected_baseline_id=selected_baseline_id,
        ),
    }


def build_forecast_lifecycle_views(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    project_id: str,
    selected_forecast_id: str | None,
) -> dict[str, object]:
    forecasts = desktop_api.list_forecast_versions(project_id)
    forecast_id = _selected_id(forecasts, selected_forecast_id, preferred_status="approved")
    forecast_lines = desktop_api.list_forecast_lines(project_id, forecast_id)
    return {
        "selected_forecast_id": forecast_id,
        "forecast_versions": FinancialsCollectionViewModel(
            title="Forecast Versions",
            subtitle="Select a governed version to inspect its reproducible ETC sources.",
            empty_state="No forecast versions exist for this project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.name,
                    status_label=item.status_label,
                    subtitle=f"Revision {item.revision} | As of {item.as_of_label}",
                    supporting_text=f"{item.generation_mode_label} | {item.currency_code}",
                    meta_text=(
                        f"Approved {item.approved_at_label}"
                        if item.approved_at_label
                        else f"Row version {item.row_version}"
                    ),
                    state={"selected": item.id == forecast_id},
                )
                for item in forecasts
            ),
            total=len(forecasts),
        ),
        "forecast_lines": FinancialsCollectionViewModel(
            title="ETC Source Lines",
            subtitle="Canonical lines from the selected forecast; amounts are not recalculated by the desktop.",
            empty_state="The selected forecast contains no ETC source lines.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.description,
                    status_label=item.source_kind_label,
                    subtitle=item.amount_label,
                    supporting_text=" | ".join(
                        part
                        for part in (
                            item.source_type_label,
                            item.source_reference_label,
                            item.source_snapshot_label,
                        )
                        if part
                    ),
                    meta_text=item.period_label or "Unphased",
                    state={
                        "costCodeId": item.cost_code_id,
                        "taskId": item.task_id,
                    },
                )
                for item in forecast_lines
            ),
            total=len(forecast_lines),
        ),
    }


def build_change_lifecycle_views(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    project_id: str,
    selected_change_id: str | None,
) -> dict[str, object]:
    changes = desktop_api.list_financial_changes(project_id)
    change_id = _selected_id(changes, selected_change_id)
    impacts = desktop_api.list_financial_change_impacts(project_id, change_id)
    return {
        "selected_change_id": change_id,
        "financial_changes": FinancialsCollectionViewModel(
            title="Financial Changes",
            subtitle="Governed requests with snapshotted bases and applied successor references.",
            empty_state="No financial changes exist for this project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.title,
                    status_label=item.status_label,
                    subtitle=f"Revision {item.revision} | Effective {item.effective_date_label}",
                    supporting_text=f"{item.reason} | Budget base: {item.base_budget_label}",
                    meta_text=f"Forecast base: {item.base_forecast_label}",
                    state={
                        "selected": item.id == change_id,
                        "appliedBudgetId": item.applied_budget_id,
                        "appliedForecastId": item.applied_forecast_id,
                        "appliedScheduleCount": item.applied_schedule_count,
                    },
                )
                for item in changes
            ),
            total=len(changes),
        ),
        "financial_change_impacts": FinancialsCollectionViewModel(
            title="Selected Change Impacts",
            subtitle="Typed deltas and source-owner application references.",
            empty_state="Select a change with impacts to inspect its applied lineage.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.description,
                    status_label=item.impact_type_label,
                    subtitle=item.amount_label,
                    supporting_text=" | ".join(
                        part
                        for part in (item.target_label, item.schedule_label)
                        if part
                    ),
                    meta_text=item.applied_reference_label or "Not applied",
                    state={
                        "costCodeId": item.cost_code_id,
                        "taskId": item.task_id,
                    },
                )
                for item in impacts
            ),
            total=len(impacts),
        ),
    }


def build_variance_views(
    desktop_api: ProjectManagementFinancialsDesktopApi,
    *,
    project_id: str,
    selected_baseline_id: str | None,
) -> dict[str, object]:
    variance = desktop_api.get_baseline_variance(project_id, selected_baseline_id)
    baseline_id = variance.selected_baseline_id
    return {
        "selected_baseline_id": baseline_id,
        "baseline_versions": FinancialsCollectionViewModel(
            title="Schedule Baseline Versions",
            subtitle="Select the approved baseline event whose stored plan-to-plan movement should be reviewed.",
            empty_state="No schedule baselines exist for this project.",
            items=tuple(
                FinancialsRecordViewModel(
                    id=item.id,
                    title=item.name,
                    status_label=item.status_label,
                    subtitle=f"Version {item.version} | Created {item.created_at_label}",
                    supporting_text=(
                        f"Approved {item.approved_at_label}"
                        if item.approved_at_label
                        else "Not approved"
                    ),
                    meta_text="Selected" if item.id == baseline_id else "",
                    state={"selected": item.id == baseline_id},
                )
                for item in variance.baselines
            ),
            total=len(variance.baselines),
        ),
        "baseline_variance": tuple(
            BaselineVarianceRowViewModel(
                task_id=item.task_id,
                task_name=item.task_name,
                start_variance_days=item.start_variance_days,
                finish_variance_days=item.finish_variance_days,
                cost_variance=item.cost_variance,
                cost_variance_label=item.cost_variance_label,
                tone=item.tone,
            )
            for item in variance.records
        ),
        "variance_basis": FinancialsDetailViewModel(
            id=baseline_id,
            title=variance.selected_baseline_label,
            status_label="Stored baseline comparison" if baseline_id else "",
            empty_state="Select a schedule baseline to review stored plan movement.",
            fields=(
                FinancialsDetailFieldViewModel("Selected baseline", variance.selected_baseline_label),
                FinancialsDetailFieldViewModel(
                    "Compared baseline",
                    variance.compared_baseline_id or "No predecessor comparison",
                ),
                FinancialsDetailFieldViewModel(
                    "Measure",
                    "Plan-to-plan schedule and planned-cost movement",
                    "This is baseline history, not actual-cost performance.",
                ),
            ) if baseline_id else (),
        ),
    }


__all__ = [
    "build_change_lifecycle_views",
    "build_forecast_lifecycle_views",
    "build_lifecycle_views",
    "build_variance_views",
]
