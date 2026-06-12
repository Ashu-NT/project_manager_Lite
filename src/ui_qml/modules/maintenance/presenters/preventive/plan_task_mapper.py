from __future__ import annotations


def plan_task_record(row) -> dict[str, object]:
    return {
        "id": row.id,
        "title": f"Step {row.sequence_no} - {row.task_template_label}",
        "subtitle": row.trigger_scope_label,
        "statusLabel": "Mandatory" if row.is_mandatory else "Optional",
        "supportingText": row.trigger_rule_summary or "Uses inherited trigger rules.",
        "metaText": f"Next due: {row.next_due_label} | Estimate: {row.estimated_minutes_override or '-'} min",
        "canPrimaryAction": True,
        "canSecondaryAction": False,
        "canTertiaryAction": False,
        "state": {
            "planTaskId": row.id,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": False,
        },
    }
