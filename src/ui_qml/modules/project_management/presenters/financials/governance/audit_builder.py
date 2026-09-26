from __future__ import annotations

from src.core.platform.api.desktop.history.audit.audit_enterprise import (
    PlatformEnterpriseAuditDesktopApi,
)
from src.ui_qml.shared.models.activity_item import (
    ActivityItemViewModel,
    humanize_action,
    icon_key_for_entity_type,
    serialize_activity_items,
)

_FINANCE_OPERATION_PREFIXES = (
    "financial_profile.",
    "project_cost_code.",
    "project_cost_code_restriction.",
    "project_budget.",
    "project_budget_line.",
    "project_planned_cost_version.",
    "project_rate_card.",
    "rate_card_line.",
    "project_forecast.",
    "project_forecast_line.",
    "financial_change_request.",
    "financial_change_impact.",
    "project_cost_entry.",
    "project_commitment.",
    "project_billing.",
    "project_billing_preparation.",
)

_SEVERITY_TONE: dict[str, str] = {
    "critical": "danger",
    "high": "danger",
    "medium": "warning",
    "low": "neutral",
}


def build_finance_audit_collection(
    audit_api: PlatformEnterpriseAuditDesktopApi | None,
    *,
    project_id: str,
    limit: int = 100,
) -> dict[str, object]:
    bounded_limit = max(1, min(int(limit), 200))
    if audit_api is None:
        return _unavailable_collection()

    result = audit_api.list_recent(
        limit=bounded_limit,
        module="project_management",
        workspace_id=project_id,
        operation_prefixes=_FINANCE_OPERATION_PREFIXES,
    )
    if not result.ok or result.data is None:
        return _unavailable_collection()

    return {
        "title": "Finance Audit",
        "subtitle": f"Latest {bounded_limit} immutable Finance audit events for this project.",
        "emptyState": "No Finance audit events have been recorded for this project.",
        "items": serialize_activity_items(_to_activity_item(entry) for entry in result.data),
    }


def _unavailable_collection() -> dict[str, object]:
    return {
        "title": "Finance Audit",
        "subtitle": "Immutable Finance audit evidence is permission protected.",
        "emptyState": "Finance audit events are unavailable for this project.",
        "items": [],
    }


def _to_activity_item(entry) -> ActivityItemViewModel:
    operation = str(entry.operation or "")
    actor_display = str(entry.actor_username or "").strip() or "System"
    entity_label = str(entry.entity_type or "Finance record").replace("_", " ").title()
    severity = str(entry.severity or "").lower()
    return ActivityItemViewModel(
        id=str(entry.id),
        title=humanize_action(operation),
        description=_evidence_text(entry),
        actor_display=actor_display,
        occurred_at=entry.timestamp,
        occurred_at_label=entry.timestamp.strftime("%d %b %Y %H:%M") if entry.timestamp else "",
        icon_key=icon_key_for_entity_type(str(entry.entity_type or "")),
        tone=_SEVERITY_TONE.get(severity, "neutral"),
        subject_display=entity_label,
        badge_label=entry.severity.capitalize() if severity in ("critical", "high") else "",
    )


def _evidence_text(entry) -> str:
    changed_fields = entry.changed_fields or {}
    if changed_fields:
        parts = []
        for field_name, change in changed_fields.items():
            before = change.get("before") if isinstance(change, dict) else None
            after = change.get("after") if isinstance(change, dict) else None
            parts.append(f"{field_name}: {before or '-'} -> {after or '-'}")
        return f"Recorded change: {'; '.join(parts)}"
    labels = tuple(
        label
        for label in (
            str(entry.category or "").strip(),
            str(entry.source or "").strip(),
        )
        if label and label != "none"
    )
    return " | ".join(labels)


__all__ = ["build_finance_audit_collection"]
