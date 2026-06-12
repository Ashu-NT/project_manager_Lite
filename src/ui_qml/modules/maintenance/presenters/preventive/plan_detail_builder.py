from __future__ import annotations


def build_plan_detail(row, *, empty_state: str, queue_row=None) -> dict[str, object]:
    if row is None:
        return {
            "id": "",
            "title": "No preventive plan selected",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": empty_state,
            "fields": [],
            "state": {},
        }
    due_state_label = getattr(queue_row, "due_state_label", "")
    due_reason = getattr(queue_row, "due_reason", "")
    plan_label = f"{row.plan_code} - {row.name}"
    return {
        "id": row.id,
        "title": plan_label,
        "statusLabel": row.status_label,
        "subtitle": f"{row.site_label} | {row.plan_type_label}",
        "description": row.description or "No preventive plan description provided.",
        "emptyState": "",
        "fields": [
            {"label": "Anchor", "value": row.anchor_label, "supportingText": row.component_label or row.system_label},
            {"label": "Trigger", "value": row.trigger_summary, "supportingText": row.trigger_mode_label},
            {"label": "Priority / Policy", "value": row.priority_label, "supportingText": row.schedule_policy_label},
            {
                "label": "Generation lead",
                "value": f"{row.generation_lead_value} {row.generation_lead_unit_label.lower()}",
                "supportingText": f"Horizon: {row.generation_horizon_count}",
            },
            {
                "label": "Next due",
                "value": row.next_due_label or "-",
                "supportingText": due_reason or due_state_label or row.next_due_counter or "",
            },
            {
                "label": "Sensor",
                "value": row.sensor_label or "-",
                "supportingText": (
                    f"{row.sensor_direction_label} {row.sensor_threshold}".strip()
                    if row.sensor_label
                    else ""
                ),
            },
            {"label": "Notes", "value": row.notes or "-", "supportingText": ""},
            {"label": "Version", "value": str(row.version), "supportingText": row.active_label},
        ],
        "state": {
            "planId": row.id,
            "siteId": row.site_id,
            "planCode": row.plan_code,
            "name": row.name,
            "assetId": row.asset_id or "",
            "componentId": row.component_id or "",
            "systemId": row.system_id or "",
            "description": row.description,
            "status": row.status,
            "planType": row.plan_type,
            "priority": row.priority,
            "triggerMode": row.trigger_mode,
            "schedulePolicy": row.schedule_policy,
            "calendarFrequencyUnit": row.calendar_frequency_unit,
            "calendarFrequencyValue": row.calendar_frequency_value,
            "generationHorizonCount": row.generation_horizon_count,
            "generationLeadValue": row.generation_lead_value,
            "generationLeadUnit": row.generation_lead_unit,
            "sensorId": row.sensor_id or "",
            "sensorThreshold": row.sensor_threshold,
            "sensorDirection": row.sensor_direction,
            "sensorResetRule": row.sensor_reset_rule,
            "requiresShutdown": row.requires_shutdown,
            "approvalRequired": row.approval_required,
            "autoGenerateWorkOrder": row.auto_generate_work_order,
            "isActive": row.is_active,
            "notes": row.notes,
            "expectedVersion": row.version,
            "canPrimaryAction": True,
            "canSecondaryAction": True,
        },
    }
