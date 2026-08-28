from __future__ import annotations

from datetime import datetime

from src.core.modules.project_management.api.desktop.common.financial_formatting import format_money
from src.core.modules.project_management.api.desktop.financials.models.billing_workspace import (
    FinancialBillingDetailDto,
    FinancialBillingReadWorkspaceDto,
    FinancialBillingTableRecordDto,
)
from src.core.modules.project_management.contracts.reads.financials.models.finance_billing_facts import (
    BillingPreparationDetailFact,
    BillingPreparationLineFact,
    BillingPreparationSummaryFact,
    BillingProfileFact,
    BillingScheduleFact,
    FinanceBillingWorkspaceFacts,
)


def serialize_finance_billing_workspace(
    source: FinanceBillingWorkspaceFacts,
    *,
    schedule_search: str = "",
    schedule_status: str = "",
    schedule_source_state: str = "",
    preparation_search: str = "",
    preparation_status: str = "",
    preparation_method: str = "",
    preparation_approval_status: str = "",
    preparation_delivery_state: str = "",
    preparation_correction_state: str = "",
    line_search: str = "",
    line_source_type: str = "",
    line_source_state: str = "",
) -> FinancialBillingReadWorkspaceDto:
    selected = source.selected_preparation
    return FinancialBillingReadWorkspaceDto(
        profile=_profile_detail(source.profile),
        selected_preparation_id=source.selected_preparation_id,
        selected_preparation=(
            _preparation_detail(selected) if selected else FinancialBillingDetailDto()
        ),
        schedule=tuple(_schedule_record(item) for item in source.schedule.items),
        schedule_page=source.schedule.page,
        schedule_page_size=source.schedule.page_size,
        schedule_total=source.schedule.total,
        schedule_sort_key=source.schedule.sort_key,
        schedule_sort_direction=source.schedule.sort_direction,
        preparations=tuple(_preparation_record(item) for item in source.preparations.items),
        preparation_page=source.preparations.page,
        preparation_page_size=source.preparations.page_size,
        preparation_total=source.preparations.total,
        preparation_sort_key=source.preparations.sort_key,
        preparation_sort_direction=source.preparations.sort_direction,
        lines=tuple(_line_record(item) for item in source.lines.items),
        line_page=source.lines.page,
        line_page_size=source.lines.page_size,
        line_total=source.lines.total,
        line_sort_key=source.lines.sort_key,
        line_sort_direction=source.lines.sort_direction,
        schedule_search=schedule_search,
        schedule_status=schedule_status,
        schedule_source_state=schedule_source_state,
        preparation_search=preparation_search,
        preparation_status=preparation_status,
        preparation_method=preparation_method,
        preparation_approval_status=preparation_approval_status,
        preparation_delivery_state=preparation_delivery_state,
        preparation_correction_state=preparation_correction_state,
        line_search=line_search,
        line_source_type=line_source_type,
        line_source_state=line_source_state,
    )


def _profile_detail(item: BillingProfileFact | None) -> FinancialBillingDetailDto:
    if item is None:
        return FinancialBillingDetailDto(
            title="Billing Profile",
            description="No PM commercial Billing Profile exists for this Project.",
        )
    return FinancialBillingDetailDto(
        id=item.id,
        title="Billing Profile",
        status_label=_label(item.status),
        subtitle=item.contract_reference,
        description="PM-owned commercial setup. This is not an Accounting customer master.",
        fields=(
            ("Contract value", format_money(item.contract_value, item.currency_code), "Projected commercial contract value"),
            ("Customer reference", item.external_customer_reference or item.customer_party_id or "-", "PM commercial reference"),
            ("Purchase order", item.purchase_order_reference or "-", "Commercial evidence"),
            ("Cost-plus markup", f"{item.cost_plus_markup_percent}%", "Applied only by governed preparation workflows"),
            ("Payment terms", f"{item.payment_terms_days} days", "Commercial preparation terms"),
            ("Retention", f"{item.retention_years} years", "Legal hold active" if item.legal_hold else "No legal hold"),
            ("Row version", str(item.row_version), item.currency_code),
        ),
        state={"currency": item.currency_code, "version": item.row_version},
    )


def _schedule_record(item: BillingScheduleFact) -> FinancialBillingTableRecordDto:
    task = " ".join(part for part in (item.task_wbs_code, item.task_name) if part) or "No task"
    return FinancialBillingTableRecordDto(
        id=item.id,
        title=item.name,
        status_label=_label(item.status),
        subtitle=format_money(item.amount, item.currency_code),
        supporting_text=item.due_date.isoformat(),
        meta_text=f"{_source_state_label(item.source_state)} | {task}",
        state={
            "currency": item.currency_code,
            "amount": str(item.amount),
            "taskId": item.task_id or "",
            "acceptanceReference": item.acceptance_reference or "",
            "sourceState": item.source_state,
            "version": item.row_version,
        },
    )


def _preparation_record(item: BillingPreparationSummaryFact) -> FinancialBillingTableRecordDto:
    return FinancialBillingTableRecordDto(
        id=item.id,
        title=item.preparation_number,
        status_label=_label(item.status),
        subtitle=f"{_label(item.billing_method)} | {item.period_start.isoformat()} to {item.period_end.isoformat()}",
        supporting_text=f"{format_money(item.total_amount, item.currency_code)} | {item.line_count} lines",
        meta_text=_delivery_truth(item),
        state={
            "approvalStatus": item.approval_status,
            "currency": item.currency_code,
            "totalAmount": str(item.total_amount),
            "lineCount": item.line_count,
            "correctionOfId": item.correction_of_preparation_id or "",
            "correctionOfNumber": item.correction_of_preparation_number,
            "latestExternalStatus": item.latest_external_status,
            "version": item.row_version,
        },
    )


def _preparation_detail(item: BillingPreparationDetailFact) -> FinancialBillingDetailDto:
    delivery_value, delivery_support = _detail_delivery_truth(item)
    outcome = (
        f"{item.latest_external_system}: {item.latest_external_status}"
        if item.latest_external_event_type
        else "No external Accounting outcome"
    )
    lock_summary = (
        f"{item.lock_count} total | {item.reserved_lock_count} reserved | "
        f"{item.finalized_lock_count} finalized | {item.released_lock_count} released"
    )
    decision_actor = item.approval_decided_by or item.approved_by or item.rejected_by or "Not decided"
    return FinancialBillingDetailDto(
        id=item.id,
        title=item.preparation_number,
        status_label=_label(item.status),
        subtitle=f"{_label(item.billing_method)} | {item.period_start.isoformat()} to {item.period_end.isoformat()}",
        description="PM-owned governed commercial handoff package; Accounting remains authoritative for invoices and receivables.",
        fields=(
            ("Preparation total", format_money(item.total_amount, item.currency_code), f"Authoritative total across {item.line_count} lines"),
            ("Approval", _label(item.approval_status) or "Not requested", item.approval_request_id or "No Platform approval request"),
            ("Requested by", item.approval_requested_by or item.submitted_by or "-", _datetime(item.approval_requested_at or item.submitted_at)),
            ("Decision", decision_actor, " | ".join(part for part in (_datetime(item.approval_decided_at), item.approval_decision_note or item.rejection_notes) if part)),
            ("Correction of", item.correction_of_preparation_number or "Original preparation", item.correction_of_preparation_id or "No correction relationship"),
            ("Source locks", lock_summary, "Authoritative duplicate-source protection"),
            ("Delivery evidence", delivery_value, delivery_support),
            ("Latest Accounting outcome", outcome, _external_support(item)),
            ("Row version", str(item.row_version), f"Created {_datetime(item.created_at)} | Updated {_datetime(item.updated_at)}"),
        ),
        state={
            "currency": item.currency_code,
            "version": item.row_version,
            "approvalRequestId": item.approval_request_id or "",
            "deliveryRequestedAt": _datetime(item.delivery_requested_at),
            "latestExternalEventType": item.latest_external_event_type,
            "externalInvoiceReference": item.latest_external_invoice_reference,
            "reconciliationReference": item.latest_reconciliation_reference,
        },
    )


def _line_record(item: BillingPreparationLineFact) -> FinancialBillingTableRecordDto:
    snapshot = f"{item.quantity} {item.unit} @ {item.unit_rate} {item.currency_code}"
    source = f"{_label(item.source_type)} | {item.source_id} rev {item.source_revision}"
    return FinancialBillingTableRecordDto(
        id=item.id,
        title=item.description,
        status_label=_label(item.source_type),
        subtitle=format_money(item.net_amount, item.currency_code),
        supporting_text=f"{_source_state_label(item.source_state)} | {snapshot}",
        meta_text=f"{item.source_date.isoformat()} | {source}",
        state={
            "preparationId": item.preparation_id,
            "sourceId": item.source_id,
            "sourceRevision": item.source_revision,
            "sourceState": item.source_state,
            "quantity": str(item.quantity),
            "unitRate": str(item.unit_rate),
            "netAmount": str(item.net_amount),
            "currency": item.currency_code,
            "taskId": item.task_id or "",
            "resourceId": item.resource_id or "",
            "sourceAmount": str(item.source_amount) if item.source_amount is not None else "",
            "markupPercent": str(item.markup_percent) if item.markup_percent is not None else "",
            "rateCardId": item.rate_card_id or "",
            "rateLineId": item.rate_line_id or "",
            "rateCardVersion": item.rate_card_version or 0,
        },
    )


def _delivery_truth(item: BillingPreparationSummaryFact) -> str:
    if item.latest_external_event_type:
        return f"External outcome: {_label(item.latest_external_status or item.latest_external_event_type)}"
    if item.delivery_requested_at:
        return "Local handoff requested; external delivery unproven"
    if item.status == "approved":
        return "Approved; ready for handoff"
    return f"Approval: {_label(item.approval_status) or 'Not requested'}"


def _detail_delivery_truth(item: BillingPreparationDetailFact) -> tuple[str, str]:
    if item.latest_external_event_type:
        return "External Accounting outcome received", _external_support(item)
    if item.delivery_requested_at:
        return "Local handoff requested", "No durable Accounting queue, delivery, or acknowledgement evidence is stored."
    if item.status == "approved":
        return "Approved; ready for handoff", "No Accounting handoff has been evidenced."
    return "No handoff requested", "Preparation governance remains within PM."


def _external_support(item: BillingPreparationDetailFact) -> str:
    parts = (
        _label(item.latest_external_event_type),
        item.latest_external_invoice_reference,
        item.latest_reconciliation_reference,
        _datetime(item.latest_external_occurred_at),
        item.latest_external_message,
    )
    return " | ".join(part for part in parts if part)


def _source_state_label(value: str) -> str:
    return "Available (released)" if value == "released" else _label(value)


def _datetime(value: datetime | None) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M") if value else ""


def _label(value: object) -> str:
    return str(value or "").replace("_", " ").strip().title()


__all__ = ["serialize_finance_billing_workspace"]
