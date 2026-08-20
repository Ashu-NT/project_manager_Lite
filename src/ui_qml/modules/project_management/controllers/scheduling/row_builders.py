from __future__ import annotations


def build_diagnostics_rows(model: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "id": item.get("id", ""),
            "message": item.get("title", ""),
            "severity": item.get("statusLabel", ""),
            "metric": item.get("metaText", ""),
            "status": item.get("subtitle", ""),
            "details": item.get("supportingText", ""),
        }
        for item in model.get("items", [])
    ]


def build_delayed_rows(model: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in model.get("items", []):
        state = dict(item.get("state", {}) or {})
        rows.append({
            "id": item.get("id", ""),
            "activityId": state.get("activityId", item.get("id", "")),
            "activity": item.get("title", ""),
            "finish": state.get("finishDateLabel", item.get("subtitle", "")),
            "deadline": state.get("deadlineLabel", ""),
            "delay": state.get("lateByLabel", item.get("supportingText", "")),
            "progress": state.get("progressLabel", item.get("metaText", "")),
            "status": item.get("statusLabel", ""),
        })
    return rows


def build_resource_rows(model: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in model.get("items", []):
        state = dict(item.get("state", {}) or {})
        rows.append({
            "id": item.get("id", ""),
            "resource": item.get("title", ""),
            "allocation": state.get("allocationLabel", ""),
            "capacity": state.get("capacityLabel", ""),
            "utilization": state.get("utilizationLabel", ""),
            "tasks": str(state.get("tasksCount", "")),
            "status": item.get("statusLabel", ""),
        })
    return rows


def build_baseline_compare_rows(model: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "id": item.get("id", ""),
            "activity": item.get("title", ""),
            "change": item.get("statusLabel", ""),
            "shift": item.get("supportingText", ""),
            "dates": item.get("subtitle", ""),
            "cost": item.get("metaText", ""),
        }
        for item in model.get("rows", [])
    ]


def build_baseline_register_rows(model: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in model.get("items", []):
        state = dict(item.get("state", {}) or {})
        rows.append({
            "id": item.get("id", ""),
            "baseline": item.get("title", ""),
            "created": state.get("createdLabel", item.get("subtitle", "")),
            "approvedBy": state.get("approvedByLabel", ""),
            "state": state.get("varianceState", ""),
            "status": state.get("statusLabel", item.get("statusLabel", "")),
            "canSubmit": bool(state.get("canSubmit", False)),
            "canApprove": bool(state.get("canApprove", False)),
            "canReject": bool(state.get("canReject", False)),
        })
    return rows


def build_dependency_rows(model: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in model.get("items", []):
        state = dict(item.get("state", {}) or {})
        rows.append({
            "id": item.get("id", ""),
            "relatedActivity": item.get("title", ""),
            "dependencyType": state.get("dependencyTypeLabel", item.get("subtitle", "")),
            "lag": state.get("lagLabel", ""),
            "direction": item.get("statusLabel", ""),
            "status": state.get("statusLabel", ""),
            "notes": item.get("supportingText", ""),
        })
    return rows


def build_constraint_rows(model: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in model.get("items", []):
        state = dict(item.get("state", {}) or {})
        rows.append({
            "id": item.get("id", ""),
            "constraint": item.get("title", ""),
            "value": state.get("constraintValue", item.get("subtitle", "")),
            "status": state.get("constraintStatus", item.get("statusLabel", "")),
            "notes": item.get("supportingText", ""),
        })
    return rows


def build_violation_rows(model: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in model.get("items", []):
        state = dict(item.get("state", {}) or {})
        rows.append({
            "id": item.get("id", ""),
            "activity": item.get("title", ""),
            "constraintType": state.get("constraintTypeLabel", item.get("subtitle", "")),
            "required": state.get("constraintDateLabel", ""),
            "computed": state.get("computedDateLabel", ""),
            "overrunDays": str(state.get("overrunDays", "")),
            "severity": state.get("severityLabel", item.get("statusLabel", "")),
            "message": state.get("message", item.get("metaText", "")),
        })
    return rows


def build_calendar_summary_rows(model: dict[str, object]) -> list[dict[str, object]]:
    working_days = [
        str(day.get("label", ""))
        for day in model.get("workingDays", [])
        if bool(day.get("checked", False))
    ]
    calendar_name = str(model.get("calendarName", "") or "Default Calendar")
    return [
        {
            "id": f"calendar:{model.get('calendarId', '') or 'default'}",
            "calendar": calendar_name,
            "workingDays": ", ".join(working_days),
            "shiftPattern": "Business week" if working_days else "No shift",
            "hoursPerDay": str(model.get("hoursPerDay", "8")),
            "exceptions": f"{len(model.get('holidays', []))} holiday(s)",
        }
    ]


def build_holiday_rows(model: dict[str, object]) -> list[dict[str, object]]:
    calendar_name = str(model.get("calendarName", "") or "Default Calendar")
    rows: list[dict[str, object]] = []
    for item in model.get("holidays", []):
        rows.append({
            "id": item.get("id", ""),
            "date": item.get("title", ""),
            "exception": item.get("subtitle", ""),
            "calendar": calendar_name,
            "details": item.get("supportingText", "") or item.get("metaText", ""),
        })
    return rows


def build_baseline_variance_rows(model: dict[str, object]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in model.get("items", []):
        state = dict(item.get("state", {}) or {})
        rows.append({
            "id": item.get("id", ""),
            "task": item.get("title", ""),
            "startVariance": state.get("startVarianceDaysLabel", ""),
            "finishVariance": state.get("finishVarianceDaysLabel", ""),
            "costVariance": state.get("costVarianceLabel", ""),
            "created": state.get("createdLabel", ""),
            "status": item.get("statusLabel", ""),
        })
    return rows


def build_leveling_move_rows(model: dict[str, object]) -> list[dict[str, object]]:
    # build_resource_leveling_state() already emits fully camelCase,
    # DataTable-column-shaped rows -- no per-field remapping needed here,
    # unlike the other builders above that flatten a generic
    # {"items": [{"state": {...}}]} collection shape.
    return list(model.get("moves", []))


__all__ = [
    "build_baseline_compare_rows",
    "build_baseline_register_rows",
    "build_baseline_variance_rows",
    "build_calendar_summary_rows",
    "build_constraint_rows",
    "build_delayed_rows",
    "build_dependency_rows",
    "build_diagnostics_rows",
    "build_holiday_rows",
    "build_leveling_move_rows",
    "build_resource_rows",
    "build_violation_rows",
]
