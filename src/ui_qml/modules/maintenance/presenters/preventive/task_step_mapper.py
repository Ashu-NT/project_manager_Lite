from __future__ import annotations


def task_step_record(row) -> dict[str, object]:
    return {
        "id": row.id,
        "title": f"Step {row.step_number}",
        "subtitle": row.instruction,
        "statusLabel": row.active_label,
        "supportingText": row.expected_result or "No expected result provided.",
        "metaText": f"Hint: {row.hint_level_label or '-'} | Sort: {row.sort_order}",
        "canPrimaryAction": True,
        "canSecondaryAction": True,
        "canTertiaryAction": False,
        "state": {
            "taskStepTemplateId": row.id,
            "isActive": row.is_active,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    }
