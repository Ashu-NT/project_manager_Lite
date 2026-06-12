from __future__ import annotations


def build_plan_task_detail(row) -> dict[str, object]:
    if row is None:
        return {
            "id": "",
            "title": "No plan task selected",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a plan task to review its sequence, trigger overrides, and estimate defaults.",
            "fields": [],
            "state": {},
        }
    return {
        "id": row.id,
        "title": row.task_template_label,
        "statusLabel": "Mandatory" if row.is_mandatory else "Optional",
        "subtitle": row.trigger_scope_label,
        "description": row.notes or "No plan-task notes provided.",
        "emptyState": "",
        "fields": [
            {"label": "Trigger", "value": row.trigger_rule_summary or row.trigger_scope_label, "supportingText": row.trigger_mode_override_label},
            {"label": "Sequence", "value": str(row.sequence_no), "supportingText": f"Estimate: {row.estimated_minutes_override or '-'} min"},
            {"label": "Sensor override", "value": row.sensor_label_override or "-", "supportingText": row.next_due_counter or ""},
            {"label": "Next due", "value": row.next_due_label or "-", "supportingText": row.next_due_counter or ""},
            {"label": "Assigned team", "value": row.default_assigned_team_id or "-", "supportingText": ""},
            {"label": "Version", "value": str(row.version), "supportingText": ""},
        ],
        "state": {
            "planTaskId": row.id,
            "planId": row.plan_id,
            "taskTemplateId": row.task_template_id,
            "triggerScope": row.trigger_scope,
            "triggerModeOverride": row.trigger_mode_override,
            "calendarFrequencyUnitOverride": "",
            "calendarFrequencyValueOverride": "",
            "sensorIdOverride": row.sensor_id_override or "",
            "sensorThresholdOverride": "",
            "sensorDirectionOverride": "",
            "sequenceNo": row.sequence_no,
            "isMandatory": row.is_mandatory,
            "defaultAssignedTeamId": row.default_assigned_team_id or "",
            "estimatedMinutesOverride": row.estimated_minutes_override,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": False,
        },
    }
