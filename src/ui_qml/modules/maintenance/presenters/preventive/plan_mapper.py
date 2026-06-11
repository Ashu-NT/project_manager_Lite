from __future__ import annotations


def plan_record(row) -> dict[str, object]:
    plan_label = f"{row.plan_code} - {row.name}"
    return {
        "id": row.id,
        "title": plan_label,
        "subtitle": row.anchor_label,
        "statusLabel": row.status_label,
        "supportingText": f"{row.plan_type_label} | {row.trigger_summary}",
        "metaText": f"Tasks: {row.plan_task_count} | Next due: {row.next_due_label}",
        "canPrimaryAction": True,
        "canSecondaryAction": True,
        "canTertiaryAction": False,
        "state": {
            "planId": row.id,
            "isActive": row.is_active,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    }
