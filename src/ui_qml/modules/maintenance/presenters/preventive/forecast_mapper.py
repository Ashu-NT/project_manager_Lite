from __future__ import annotations


def forecast_record(row) -> dict[str, object]:
    return {
        "id": row.instance_id,
        "title": row.due_at_label,
        "subtitle": row.instance_status_label,
        "statusLabel": row.planner_state_label,
        "supportingText": f"Window opens: {row.generation_window_opens_at_label}",
        "metaText": (
            f"WR: {row.generated_work_request_id or '-'} | "
            f"WO: {row.generated_work_order_id or '-'} | "
            f"Completed: {row.completed_at_label or '-'}"
        ),
        "canPrimaryAction": False,
        "canSecondaryAction": False,
        "canTertiaryAction": False,
        "state": {},
    }
