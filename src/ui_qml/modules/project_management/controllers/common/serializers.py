from __future__ import annotations

from src.ui_qml.modules.project_management.view_models.dashboard import (
    ProjectDashboardChartViewModel,
    ProjectDashboardOverviewViewModel,
    ProjectDashboardPanelViewModel,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailViewModel,
    FinancialsOverviewViewModel,
    FinancialsRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.projects import (
    ProjectCatalogOverviewViewModel,
    ProjectDetailViewModel,
    ProjectRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceCatalogOverviewViewModel,
    ResourceDetailViewModel,
    ResourceEmployeeOptionViewModel,
    ResourceRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.register import (
    RegisterCollectionViewModel,
    RegisterDetailViewModel,
    RegisterOverviewViewModel,
    RegisterRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.scheduling import (
    SchedulingBaselineCompareViewModel,
    SchedulingCalendarViewModel,
    SchedulingCollectionViewModel,
    SchedulingOverviewViewModel,
    SchedulingRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.tasks import (
    TaskCatalogOverviewViewModel,
    TaskDetailViewModel,
    TaskRecordViewModel,
)
from src.ui_qml.modules.project_management.view_models.workspace import (
    ProjectManagementWorkspaceViewModel,
)


def serialize_workspace_view_model(
    view_model: ProjectManagementWorkspaceViewModel,
) -> dict[str, str]:
    return {
        "routeId": view_model.route_id,
        "title": view_model.title,
        "summary": view_model.summary,
        "migrationStatus": view_model.migration_status,
        "legacyRuntimeStatus": view_model.legacy_runtime_status,
    }


def serialize_dashboard_overview_view_model(
    view_model: ProjectDashboardOverviewViewModel,
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


def serialize_selector_options(view_models) -> list[dict[str, str]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
        }
        for view_model in view_models
    ]


def serialize_dashboard_section_view_models(view_models) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "emptyState": view_model.empty_state,
            "items": [
                {
                    "id": item.id,
                    "title": item.title,
                    "statusLabel": item.status_label,
                    "subtitle": item.subtitle,
                    "supportingText": item.supporting_text,
                    "metaText": item.meta_text,
                    "state": dict(item.state),
                }
                for item in view_model.items
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_panel_view_models(
    view_models: tuple[ProjectDashboardPanelViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "hint": view_model.hint,
            "emptyState": view_model.empty_state,
            "rows": [
                {
                    "label": row.label,
                    "value": row.value,
                    "supportingText": row.supporting_text,
                    "tone": row.tone,
                }
                for row in view_model.rows
            ],
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in view_model.metrics
            ],
        }
        for view_model in view_models
    ]


def serialize_dashboard_chart_view_models(
    view_models: tuple[ProjectDashboardChartViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "title": view_model.title,
            "subtitle": view_model.subtitle,
            "chartType": view_model.chart_type,
            "emptyState": view_model.empty_state,
            "points": [
                {
                    "label": point.label,
                    "value": point.value,
                    "valueLabel": point.value_label,
                    "supportingText": point.supporting_text,
                    "targetValue": point.target_value,
                    "tone": point.tone,
                }
                for point in view_model.points
            ],
        }
        for view_model in view_models
    ]


def serialize_project_catalog_overview_view_model(
    view_model: ProjectCatalogOverviewViewModel,
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


def serialize_financials_collection_view_model(
    view_model: FinancialsCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_financials_record_view_models(view_model.items),
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


def serialize_project_record_view_models(
    view_models: tuple[ProjectRecordViewModel, ...],
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


def serialize_project_detail_view_model(
    view_model: ProjectDetailViewModel,
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


def serialize_resource_catalog_overview_view_model(
    view_model: ResourceCatalogOverviewViewModel,
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


def serialize_resource_employee_option_view_models(
    view_models: tuple[ResourceEmployeeOptionViewModel, ...],
) -> list[dict[str, object]]:
    return [
        {
            "value": view_model.value,
            "label": view_model.label,
            "name": view_model.name,
            "title": view_model.title,
            "contact": view_model.contact,
            "context": view_model.context,
            "isActive": view_model.is_active,
        }
        for view_model in view_models
    ]


def serialize_resource_record_view_models(
    view_models: tuple[ResourceRecordViewModel, ...],
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


def serialize_resource_detail_view_model(
    view_model: ResourceDetailViewModel,
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


def serialize_register_overview_view_model(
    view_model: RegisterOverviewViewModel,
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


def serialize_register_record_view_models(
    view_models: tuple[RegisterRecordViewModel, ...],
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


def serialize_register_collection_view_model(
    view_model: RegisterCollectionViewModel,
) -> dict[str, object]:
    return {
        "title": view_model.title,
        "subtitle": view_model.subtitle,
        "emptyState": view_model.empty_state,
        "items": serialize_register_record_view_models(view_model.items),
    }


def serialize_register_detail_view_model(
    view_model: RegisterDetailViewModel,
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


def serialize_task_catalog_overview_view_model(
    view_model: TaskCatalogOverviewViewModel,
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


def serialize_task_record_view_models(
    view_models: tuple[TaskRecordViewModel, ...],
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


def serialize_task_detail_view_model(
    view_model: TaskDetailViewModel,
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


__all__ = [
    "serialize_dashboard_chart_view_models",
    "serialize_dashboard_overview_view_model",
    "serialize_dashboard_panel_view_models",
    "serialize_dashboard_section_view_models",
    "serialize_financials_collection_view_model",
    "serialize_financials_detail_view_model",
    "serialize_financials_overview_view_model",
    "serialize_financials_record_view_models",
    "serialize_project_catalog_overview_view_model",
    "serialize_project_detail_view_model",
    "serialize_project_record_view_models",
    "serialize_register_collection_view_model",
    "serialize_register_detail_view_model",
    "serialize_register_overview_view_model",
    "serialize_register_record_view_models",
    "serialize_resource_catalog_overview_view_model",
    "serialize_resource_detail_view_model",
    "serialize_resource_employee_option_view_models",
    "serialize_resource_record_view_models",
    "serialize_scheduling_baselines_view_model",
    "serialize_scheduling_calendar_view_model",
    "serialize_scheduling_collection_view_model",
    "serialize_scheduling_overview_view_model",
    "serialize_scheduling_record_view_models",
    "serialize_selector_options",
    "serialize_task_catalog_overview_view_model",
    "serialize_task_detail_view_model",
    "serialize_task_record_view_models",
    "serialize_workspace_view_model",
]
