from __future__ import annotations

from typing import Any

from src.ui_qml.modules.project_management.view_models.resources import (
    ResourceRecordViewModel,
)

from .detail_builder import build_resource_state

def to_resource_record_view_model(resource: Any) -> ResourceRecordViewModel:
    state = build_resource_state(resource)
    subtitle_parts = [state["role"], state["workerTypeLabel"]]
    subtitle_values = [part for part in subtitle_parts if part]
    meta_parts = []
    if state["employeeContext"] and state["employeeContext"] != "-":
        meta_parts.append(state["employeeContext"])
    if state["contact"]:
        meta_parts.append(state["contact"])
    return ResourceRecordViewModel(
        id=resource.id,
        title=resource.name,
        status_label=resource.active_label,
        subtitle=" | ".join(subtitle_values) or "No role assigned",
        supporting_text=(
            f"{state['costTypeLabel']} | {state['hourlyRateLabel']} | Capacity {state['capacityLabel']}"
        ),
        meta_text=" | ".join(meta_parts),
        state=state,
    )
