from __future__ import annotations


def queue_record(row) -> dict[str, object]:
    return {
        "id": row.plan_id,
        "title": row.plan_label,
        "subtitle": row.anchor_label,
        "statusLabel": row.due_state_label,
        "supportingText": f"{row.plan_status_label} | {row.trigger_label}",
        "metaText": f"Next due: {row.next_due_label} | {row.due_reason}",
        "canPrimaryAction": True,
        "canSecondaryAction": True,
        "canTertiaryAction": False,
        "state": {
            "planId": row.plan_id,
            "expectedVersion": row.version,
            "isDueSoon": row.is_due_soon,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    }
