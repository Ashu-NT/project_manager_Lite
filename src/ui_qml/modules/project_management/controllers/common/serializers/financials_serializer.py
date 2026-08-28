from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.financials import (
    BaselineVarianceRowViewModel,
    FinancialsCollectionViewModel,
    FinancialsCommitmentSummaryViewModel,
    FinancialsDetailViewModel,
    FinancialsOverviewViewModel,
    FinancialsRecordViewModel,
)


def serialize_financials_overview_view_model(
    view_model: FinancialsOverviewViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "metrics": [
            {
                "label": metric.label,
                "value": metric.value,
                "supportingText": metric.supporting_text,
            }
            for metric in view_model.metrics
        ],
    }


def serialize_financials_record_view_models(
    view_models: tuple[FinancialsRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "costCode": str(view_model.state.get("costCode", "") or ""),
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "taskName": str(view_model.state.get("taskName", "") or ""),
            "plannedAmountLabel": str(view_model.state.get("plannedAmountLabel", "") or ""),
            "forecastAmountLabel": str(view_model.state.get("forecastAmountLabel", "") or ""),
            "committedAmountLabel": str(view_model.state.get("committedAmountLabel", "") or ""),
            "actualAmountLabel": str(view_model.state.get("actualAmountLabel", "") or ""),
            "commitmentStatusLabel": str(view_model.state.get("commitmentStatusLabel", "") or ""),
            "incurredDateLabel": str(view_model.state.get("incurredDateLabel", "") or ""),
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_financials_commitment_summary_view_model(
    vm: FinancialsCommitmentSummaryViewModel,
) -> dict[str, object]:
    return {
        "approvedBudgetLabel": vm.approved_budget_label,
        "postedActualLabel": vm.posted_actual_label,
        "openCommitmentLabel": vm.open_commitment_label,
        "availableAfterCommitmentLabel": vm.available_after_commitment_label,
        "commitmentRatePct": vm.commitment_rate_pct,
    }


def serialize_financials_baseline_variance_view_models(
    rows: tuple,
) -> list[dict[str, object]]:
    return [
        {
            "taskId": row.task_id,
            "taskName": row.task_name,
            "startVarianceDays": row.start_variance_days,
            "finishVarianceDays": row.finish_variance_days,
            "costVariance": row.cost_variance,
            "costVarianceLabel": row.cost_variance_label,
            "tone": row.tone,
        }
        for row in rows
    ]


def serialize_financials_collection_view_model(
    view_model: FinancialsCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_financials_record_view_models(view_model.items),
        "page": view_model.page,
        "pageSize": view_model.page_size,
        "total": view_model.total,
    }


def serialize_financials_detail_view_model(
    view_model: FinancialsDetailViewModel,
) -> dict[str, object]:
    return {
        "id": view_model.id,
        "title": view_model.title,
        "statusLabel": view_model.status_label,
        "subtitle": view_model.subtitle,
        "description": view_model.description,
        "emptyState": view_model.empty_state,
        "fields": [
            {
                "label": field.label,
                "value": field.value,
                "supportingText": field.supporting_text,
            }
            for field in view_model.fields
        ],
        "state": dict(view_model.state),
    }


__all__ = [
    "serialize_financials_baseline_variance_view_models",
    "serialize_financials_collection_view_model",
    "serialize_financials_commitment_summary_view_model",
    "serialize_financials_detail_view_model",
    "serialize_financials_overview_view_model",
    "serialize_financials_record_view_models",
]
