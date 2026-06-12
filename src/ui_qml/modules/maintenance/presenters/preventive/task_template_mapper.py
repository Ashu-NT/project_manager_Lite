from __future__ import annotations


def task_template_record(row) -> dict[str, object]:
    return {
        "id": row.id,
        "title": f"{row.task_template_code} - {row.name}",
        "subtitle": row.maintenance_type_label,
        "statusLabel": row.template_status_label,
        "supportingText": f"Revision {row.revision_no} | {row.step_count} steps | {row.active_label}",
        "metaText": f"Estimated minutes: {row.estimated_minutes or '-'} | Skill: {row.required_skill or '-'}",
        "canPrimaryAction": True,
        "canSecondaryAction": True,
        "canTertiaryAction": False,
        "state": {
            "taskTemplateId": row.id,
            "isActive": row.is_active,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    }
