from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.preventive import (
    MaintenancePreventiveWorkspaceViewModel,
)


def serialize_preventive_workspace_state(
    view_model: MaintenancePreventiveWorkspaceViewModel,
) -> dict[str, object]:
    return {
        "overview": {
            "title": view_model.overview.title,
            "subtitle": view_model.overview.subtitle,
            "metrics": [
                {
                    "label": metric.label,
                    "value": metric.value,
                    "supportingText": metric.supporting_text,
                }
                for metric in view_model.overview.metrics
            ],
        },
        "queueState": dict(view_model.queue_state),
        "planLibraryState": dict(view_model.plan_library_state),
        "templateLibraryState": dict(view_model.template_library_state),
        "planFormOptions": dict(view_model.plan_form_options),
        "planTaskFormOptions": dict(view_model.plan_task_form_options),
        "templateFormOptions": dict(view_model.template_form_options),
        "stepFormOptions": dict(view_model.step_form_options),
        "emptyState": view_model.empty_state,
    }


__all__ = ["serialize_preventive_workspace_state"]
