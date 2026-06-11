from __future__ import annotations

from src.ui_qml.modules.maintenance.view_models.planner import (
    MaintenancePlannerPreventiveRowViewModel,
)


def preventive_row(row) -> MaintenancePlannerPreventiveRowViewModel:
    return MaintenancePlannerPreventiveRowViewModel(
        plan_id=row.plan_id,
        plan_label=row.plan_label,
        anchor_label=row.anchor_label,
        due_state_label=row.due_state_label,
        due_reason=row.due_reason,
        generation_target_label=row.generation_target_label,
        trigger_label=row.trigger_label,
        next_due_label=row.next_due_label,
        is_due_soon=row.is_due_soon,
    )
