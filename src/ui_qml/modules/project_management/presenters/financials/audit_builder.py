from __future__ import annotations

from src.core.platform.api.desktop.history.audit.audit_enterprise import (
    PlatformEnterpriseAuditDesktopApi,
)
from src.ui_qml.modules.project_management.presenters.common.activity_log_builder import (
    status_label_for_action,
)
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsRecordViewModel,
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


def build_finance_audit_collection(
    audit_api: PlatformEnterpriseAuditDesktopApi | None,
    *,
    project_id: str,
    limit: int = 100,
) -> FinancialsCollectionViewModel:
    bounded_limit = max(1, min(int(limit), 200))
    if audit_api is None:
        return _unavailable_collection(bounded_limit)

    result = audit_api.list_recent(
        limit=bounded_limit,
        module="project_management",
        workspace_id=project_id,
        operation_prefixes=_FINANCE_OPERATION_PREFIXES,
    )
    if not result.ok or result.data is None:
        return _unavailable_collection(bounded_limit)

    items = tuple(_build_record(entry) for entry in result.data)
    return FinancialsCollectionViewModel(
        title="Finance Audit",
        subtitle=f"Latest {bounded_limit} immutable Finance audit events for this project.",
        empty_state="No Finance audit events have been recorded for this project.",
        items=items,
        page=1,
        page_size=bounded_limit,
        total=len(items),
    )


def _unavailable_collection(limit: int) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Finance Audit",
        subtitle="Immutable Finance audit evidence is permission protected.",
        empty_state="Finance audit events are unavailable for this project.",
        page=1,
        page_size=limit,
        total=0,
    )


def _build_record(entry) -> FinancialsRecordViewModel:
    operation = str(entry.operation or "")
    operation_label = operation.replace(".", " ").replace("_", " ").title()
    entity_label = str(entry.entity_type or "Finance record").replace("_", " ").title()
    actor_label = str(entry.actor_username or "").strip() or "System"
    evidence = _evidence_text(entry)
    return FinancialsRecordViewModel(
        id=str(entry.id),
        title=f"{actor_label} - {operation_label}",
        status_label=(
            str(entry.severity or "").capitalize()
            or status_label_for_action(operation)
        ),
        subtitle=entity_label,
        supporting_text=evidence,
        meta_text=(
            entry.timestamp.strftime("%d %b %Y %H:%M") if entry.timestamp else ""
        ),
        can_primary_action=False,
        can_secondary_action=False,
        state={
            "operation": operation,
            "source": str(entry.source or ""),
            "complianceTag": str(entry.compliance_tag or ""),
        },
    )


def _evidence_text(entry) -> str:
    old_value = str(entry.old_value or "").strip()
    new_value = str(entry.new_value or "").strip()
    if old_value or new_value:
        return f"Recorded change: {old_value or '-'} -> {new_value or '-'}"
    labels = tuple(
        label
        for label in (
            str(entry.compliance_tag or "").strip(),
            str(entry.source or "").strip(),
        )
        if label and label != "none"
    )
    return " | ".join(labels)


__all__ = ["build_finance_audit_collection"]
