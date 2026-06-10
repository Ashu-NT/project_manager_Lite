from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.common.serializers.selector_serializer import (
    serialize_selector_options,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingBaselineCompareViewModel,
    SchedulingCalendarViewModel,
    SchedulingCollectionViewModel,
    SchedulingDetailViewModel,
    SchedulingOverviewViewModel,
    SchedulingRecordViewModel,
)


def serialize_scheduling_overview_view_model(
    view_model: SchedulingOverviewViewModel,
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


def serialize_scheduling_record_view_models(
    view_models: tuple[SchedulingRecordViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "id": view_model.id,
            "title": view_model.title,
            "statusLabel": view_model.status_label,
            "subtitle": view_model.subtitle,
            "supportingText": view_model.supporting_text,
            "metaText": view_model.meta_text,
            "canPrimaryAction": view_model.can_primary_action,
            "canSecondaryAction": view_model.can_secondary_action,
            "canTertiaryAction": view_model.can_tertiary_action,
            "state": dict(view_model.state),
        }
        for view_model in view_models
    ]


def serialize_scheduling_collection_view_model(
    view_model: SchedulingCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_scheduling_record_view_models(view_model.items),
    }


def serialize_scheduling_calendar_view_model(
    view_model: SchedulingCalendarViewModel,
) -> dict[str, object]:
    return {
        "summaryText": view_model.summary_text,
        "workingDays": [
            {
                "index": option.index,
                "label": option.label,
                "checked": option.checked,
            }
            for option in view_model.working_day_options
        ],
        "hoursPerDay": view_model.hours_per_day,
        "holidays": serialize_scheduling_record_view_models(view_model.holidays),
        "emptyState": view_model.empty_state,
    }


def serialize_scheduling_baselines_view_model(
    view_model: SchedulingBaselineCompareViewModel,
) -> dict[str, object]:
    return {
        "options": serialize_selector_options(view_model.options),
        "selectedBaselineAId": view_model.selected_baseline_a_id,
        "selectedBaselineBId": view_model.selected_baseline_b_id,
        "includeUnchanged": view_model.include_unchanged,
        "summaryText": view_model.summary_text,
        "rows": serialize_scheduling_record_view_models(view_model.rows),
        "emptyState": view_model.empty_state,
    }


def serialize_scheduling_detail_view_model(
    view_model: SchedulingDetailViewModel,
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
    "serialize_scheduling_baselines_view_model",
    "serialize_scheduling_calendar_view_model",
    "serialize_scheduling_collection_view_model",
    "serialize_scheduling_detail_view_model",
    "serialize_scheduling_overview_view_model",
    "serialize_scheduling_record_view_models",
]
