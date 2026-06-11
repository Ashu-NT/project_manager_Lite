from __future__ import annotations


def build_task_template_detail(row) -> dict[str, object]:
    if row is None:
        return {
            "id": "",
            "title": "No task template selected",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a task template to inspect revision status, required skills, and its step library.",
            "fields": [],
            "state": {},
        }
    return {
        "id": row.id,
        "title": f"{row.task_template_code} - {row.name}",
        "statusLabel": row.template_status_label,
        "subtitle": row.maintenance_type_label,
        "description": row.description or "No task template description provided.",
        "emptyState": "",
        "fields": [
            {"label": "Revision", "value": str(row.revision_no), "supportingText": row.active_label},
            {"label": "Estimate", "value": str(row.estimated_minutes or "-"), "supportingText": "Minutes"},
            {"label": "Required skill", "value": row.required_skill or "-", "supportingText": ""},
            {
                "label": "Permits / Shutdown",
                "value": "Permit required" if row.requires_permit else "Permit not required",
                "supportingText": "Shutdown required" if row.requires_shutdown else "No shutdown required",
            },
            {"label": "Notes", "value": row.notes or "-", "supportingText": ""},
            {"label": "Version", "value": str(row.version), "supportingText": f"{row.step_count} steps"},
        ],
        "state": {
            "taskTemplateId": row.id,
            "taskTemplateCode": row.task_template_code,
            "name": row.name,
            "description": row.description,
            "maintenanceType": row.maintenance_type,
            "revisionNo": row.revision_no,
            "templateStatus": row.template_status,
            "estimatedMinutes": row.estimated_minutes,
            "requiredSkill": row.required_skill,
            "requiresShutdown": row.requires_shutdown,
            "requiresPermit": row.requires_permit,
            "isActive": row.is_active,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    }
