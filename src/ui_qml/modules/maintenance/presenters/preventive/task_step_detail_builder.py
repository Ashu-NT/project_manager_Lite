from __future__ import annotations


def build_task_step_detail(row) -> dict[str, object]:
    if row is None:
        return {
            "id": "",
            "title": "No task step selected",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a task step to review instructions, hinting, and confirmation requirements.",
            "fields": [],
            "state": {},
        }
    return {
        "id": row.id,
        "title": f"Step {row.step_number}",
        "statusLabel": row.active_label,
        "subtitle": row.instruction,
        "description": row.expected_result or "No expected result provided.",
        "emptyState": "",
        "fields": [
            {"label": "Sort order", "value": str(row.sort_order), "supportingText": row.hint_level_label or ""},
            {
                "label": "Capture requirements",
                "value": "Confirmation" if row.requires_confirmation else "No confirmation",
                "supportingText": (
                    ("Measurement " if row.requires_measurement else "")
                    + ("Photo" if row.requires_photo else "")
                ).strip() or "No extra capture requirements",
            },
            {"label": "Measurement unit", "value": row.measurement_unit or "-", "supportingText": ""},
            {"label": "Hint text", "value": row.hint_text or "-", "supportingText": ""},
            {"label": "Notes", "value": row.notes or "-", "supportingText": ""},
            {"label": "Version", "value": str(row.version), "supportingText": ""},
        ],
        "state": {
            "taskStepTemplateId": row.id,
            "taskTemplateId": row.task_template_id,
            "stepNumber": row.step_number,
            "sortOrder": row.sort_order,
            "instruction": row.instruction,
            "expectedResult": row.expected_result,
            "hintLevel": row.hint_level,
            "hintText": row.hint_text,
            "requiresConfirmation": row.requires_confirmation,
            "requiresMeasurement": row.requires_measurement,
            "requiresPhoto": row.requires_photo,
            "measurementUnit": row.measurement_unit,
            "isActive": row.is_active,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    }
