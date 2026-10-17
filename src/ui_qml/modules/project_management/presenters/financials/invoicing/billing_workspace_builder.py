from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from src.core.modules.project_management.api.desktop.common.financial_formatting import (
    format_money,
)
from src.core.modules.project_management.contracts.reads.financials.budgets.models.budget_facts import (
    FinancePageFacts,
)
from src.core.modules.project_management.contracts.reads.financials.invoicing.models.billing_facts import (
    AccountingStatusFact,
    BillingPreparationDetailFact,
    BillingPreparationLineFact,
    BillingPreparationSummaryFact,
    BillingProfileFact,
    BillingScheduleFact,
    BillingSourceOptionFact,
    FinanceBillingWorkspaceFacts,
)
from src.core.platform.domain.finance.money import canonical_decimal_text
from src.ui_qml.modules.project_management.view_models.financials import (
    FinancialsCollectionViewModel,
    FinancialsDetailFieldViewModel,
    FinancialsDetailViewModel,
    FinancialsRecordViewModel,
)


def build_billing_source_options(page: FinancePageFacts[BillingSourceOptionFact]) -> dict[str, object]:
    return {
        "ok": True,
        "items": [
            {"value": item.source_id, "label": item.label, "sourceType": item.source_type,
             "sourceDate": item.source_date.isoformat(), "amount": canonical_decimal_text(item.amount),
             "currencyCode": item.currency_code}
            for item in page.items
        ],
        "total": page.total, "page": page.page, "pageSize": page.page_size,
        "hasMore": page.page * page.page_size < page.total,
    }


class FinanceBillingViews(TypedDict):
    billing_profile: FinancialsDetailViewModel
    selected_billing_preparation_id: str
    selected_billing_preparation: FinancialsDetailViewModel
    billing_schedule: FinancialsCollectionViewModel
    billing_preparations: FinancialsCollectionViewModel
    billing_preparation_lines: FinancialsCollectionViewModel
    billing_schedule_sort_key: str
    billing_schedule_sort_direction: str
    billing_preparation_sort_key: str
    billing_preparation_sort_direction: str
    billing_line_sort_key: str
    billing_line_sort_direction: str
    billing_schedule_search: str
    billing_schedule_status: str
    billing_schedule_source_state: str
    billing_preparation_search: str
    billing_preparation_status: str
    billing_preparation_method: str
    billing_preparation_approval_status: str
    billing_preparation_delivery_state: str
    billing_preparation_correction_state: str
    billing_line_search: str
    billing_line_source_type: str
    billing_line_source_state: str


def build_billing_workspace_views(
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
) -> FinanceBillingViews:
    return {
        "billing_profile": _profile_detail(
            source.profile, can_create=source.can_manage_billing
        ),
        "selected_billing_preparation_id": source.selected_preparation_id,
        "selected_billing_preparation": (
            _preparation_detail(source.selected_preparation)
            if source.selected_preparation is not None
            else FinancialsDetailViewModel(
                empty_state="Select a Billing Preparation to inspect governance and Accounting outcome evidence."
            )
        ),
        "billing_schedule": FinancialsCollectionViewModel(
            title="Billing Schedule",
            subtitle="PM-owned commercial schedule evidence and source-consumption state.",
            empty_state="No Billing Schedule lines match the current filters.",
            items=tuple(_schedule_record(item) for item in source.schedule.items),
            page=source.schedule.page,
            page_size=source.schedule.page_size,
            total=source.schedule.total,
        ),
        "billing_preparations": FinancialsCollectionViewModel(
            title="Billing Preparations",
            subtitle="Governed PM commercial handoff packages; not Accounting invoices.",
            empty_state="No Billing Preparations match the current filters.",
            items=tuple(
                _preparation_record(item) for item in source.preparations.items
            ),
            page=source.preparations.page,
            page_size=source.preparations.page_size,
            total=source.preparations.total,
        ),
        "billing_preparation_lines": FinancialsCollectionViewModel(
            title="Selected Preparation Lines",
            subtitle="Immutable source, rate, markup, and currency snapshots.",
            empty_state=(
                "Select a Billing Preparation."
                if not source.selected_preparation_id
                else "No Preparation Lines match the current filters."
            ),
            items=tuple(_line_record(item) for item in source.lines.items),
            page=source.lines.page,
            page_size=source.lines.page_size,
            total=source.lines.total,
        ),
        "billing_schedule_sort_key": source.schedule.sort_key,
        "billing_schedule_sort_direction": source.schedule.sort_direction,
        "billing_preparation_sort_key": source.preparations.sort_key,
        "billing_preparation_sort_direction": source.preparations.sort_direction,
        "billing_line_sort_key": source.lines.sort_key,
        "billing_line_sort_direction": source.lines.sort_direction,
        "billing_schedule_search": schedule_search,
        "billing_schedule_status": schedule_status,
        "billing_schedule_source_state": schedule_source_state,
        "billing_preparation_search": preparation_search,
        "billing_preparation_status": preparation_status,
        "billing_preparation_method": preparation_method,
        "billing_preparation_approval_status": preparation_approval_status,
        "billing_preparation_delivery_state": preparation_delivery_state,
        "billing_preparation_correction_state": preparation_correction_state,
        "billing_line_search": line_search,
        "billing_line_source_type": line_source_type,
        "billing_line_source_state": line_source_state,
    }


def build_accounting_status_collection(
    source: FinancePageFacts[AccountingStatusFact],
) -> FinancialsCollectionViewModel:
    return FinancialsCollectionViewModel(
        title="Accounting Handoffs & Outcomes",
        subtitle=(
            "Transport delivery is not Accounting acknowledgement. "
            "Acknowledgement is not invoice issuance; reconciliation is not payment."
        ),
        empty_state="No Accounting outcome evidence is available for this project.",
        items=tuple(_accounting_record(item) for item in source.items),
        page=source.page,
        page_size=source.page_size,
        total=source.total,
    )


def _profile_detail(
    item: BillingProfileFact | None, *, can_create: bool
) -> FinancialsDetailViewModel:
    if item is None:
        return FinancialsDetailViewModel(
            title="Billing Profile",
            empty_state="No Billing Profile exists for this Project.",
            description="No PM commercial Billing Profile exists for this Project.",
            state={"canCreate": can_create},
        )
    return FinancialsDetailViewModel(
        id=item.id,
        title="Billing Profile",
        status_label=_label(item.status),
        subtitle=item.contract_reference,
        description="PM-owned commercial setup. This is not an Accounting customer master.",
        fields=tuple(
            FinancialsDetailFieldViewModel(*field)
            for field in (
                (
                    "Contract value",
                    format_money(item.contract_value, item.currency_code),
                    "Projected commercial contract value",
                ),
                (
                    "Customer reference",
                    item.external_customer_reference or item.customer_party_id or "-",
                    "PM commercial reference",
                ),
                (
                    "Purchase order",
                    item.purchase_order_reference or "-",
                    "Commercial evidence",
                ),
                (
                    "Cost-plus markup",
                    f"{item.cost_plus_markup_percent}%",
                    "Applied only by governed preparation workflows",
                ),
                (
                    "Payment terms",
                    f"{item.payment_terms_days} days",
                    "Commercial preparation terms",
                ),
                (
                    "Retention",
                    f"{item.retention_years} years",
                    "Legal hold active" if item.legal_hold else "No legal hold",
                ),
                ("Row version", str(item.row_version), item.currency_code),
            )
        ),
        state={
            "currency": item.currency_code,
            "version": item.row_version,
            "canActivate": item.can_activate,
            "canAddScheduleLine": item.can_add_schedule_line,
            "canCreatePreparation": item.can_create_preparation,
            "canCreate": False,
        },
    )


def _schedule_record(item: BillingScheduleFact) -> FinancialsRecordViewModel:
    task = (
        " ".join(part for part in (item.task_wbs_code, item.task_name) if part)
        or "No task"
    )
    return FinancialsRecordViewModel(
        can_primary_action=False,
        can_secondary_action=False,
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
            "canMarkReady": item.can_mark_ready,
        },
    )


def _preparation_record(
    item: BillingPreparationSummaryFact,
) -> FinancialsRecordViewModel:
    return FinancialsRecordViewModel(
        can_primary_action=False,
        can_secondary_action=False,
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


def _preparation_detail(
    item: BillingPreparationDetailFact,
) -> FinancialsDetailViewModel:
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
    decision_actor = (
        item.approval_decided_by
        or item.approved_by
        or item.rejected_by
        or "Not decided"
    )
    return FinancialsDetailViewModel(
        id=item.id,
        title=item.preparation_number,
        status_label=_label(item.status),
        subtitle=f"{_label(item.billing_method)} | {item.period_start.isoformat()} to {item.period_end.isoformat()}",
        description="PM-owned governed commercial handoff package; Accounting remains authoritative for invoices and receivables.",
        fields=tuple(
            FinancialsDetailFieldViewModel(*field)
            for field in (
                (
                    "Preparation total",
                    format_money(item.total_amount, item.currency_code),
                    f"Authoritative total across {item.line_count} lines",
                ),
                (
                    "Approval",
                    _label(item.approval_status) or "Not requested",
                    item.approval_request_id or "No Platform approval request",
                ),
                (
                    "Requested by",
                    item.approval_requested_by or item.submitted_by or "-",
                    _datetime(item.approval_requested_at or item.submitted_at),
                ),
                (
                    "Decision",
                    decision_actor,
                    " | ".join(
                        part
                        for part in (
                            _datetime(item.approval_decided_at),
                            item.approval_decision_note or item.rejection_notes,
                        )
                        if part
                    ),
                ),
                (
                    "Correction of",
                    item.correction_of_preparation_number or "Original preparation",
                    item.correction_of_preparation_id or "No correction relationship",
                ),
                (
                    "Source locks",
                    lock_summary,
                    "Authoritative duplicate-source protection",
                ),
                ("Delivery evidence", delivery_value, delivery_support),
                ("Latest Accounting outcome", outcome, _external_support(item)),
                (
                    "Row version",
                    str(item.row_version),
                    f"Created {_datetime(item.created_at)} | Updated {_datetime(item.updated_at)}",
                ),
            )
        ),
        state={
            "currency": item.currency_code,
            "version": item.row_version,
            "approvalRequestId": item.approval_request_id or "",
            "deliveryRequestedAt": _datetime(item.delivery_requested_at),
            "latestExternalEventType": item.latest_external_event_type,
            "externalInvoiceReference": item.latest_external_invoice_reference,
            "reconciliationReference": item.latest_reconciliation_reference,
            "canEditDraft": item.can_edit_draft,
            "canAddSource": item.can_add_source,
            "canRemoveSource": item.can_remove_source,
            "canSubmit": item.can_submit,
            "canApprove": item.can_approve,
            "canReject": item.can_reject,
            "canCancel": item.can_cancel,
            "canCreateCorrection": item.can_create_correction,
            "canRequestDelivery": item.can_request_delivery,
            "handoffDenialReason": item.handoff_denial_reason,
            "handoffDenialMessage": item.handoff_denial_message,
            "canViewAccountingStatus": item.can_view_accounting_status,
        },
    )


def _line_record(item: BillingPreparationLineFact) -> FinancialsRecordViewModel:
    snapshot = (
        f"{item.quantity} {item.unit} @ {item.unit_rate} {item.currency_code}"
        if item.unit_rate is not None
        else "Rate evidence restricted"
    )
    source = f"{_label(item.source_type)} | {item.source_id} rev {item.source_revision}"
    return FinancialsRecordViewModel(
        can_primary_action=False,
        can_secondary_action=False,
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
            "unitRate": str(item.unit_rate) if item.unit_rate is not None else "",
            "netAmount": str(item.net_amount),
            "currency": item.currency_code,
            "taskId": item.task_id or "",
            "resourceId": item.resource_id or "",
            "sourceAmount": str(item.source_amount)
            if item.source_amount is not None
            else "",
            "markupPercent": str(item.markup_percent)
            if item.markup_percent is not None
            else "",
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
        return (
            "Local handoff requested",
            "No durable Accounting queue, delivery, or acknowledgement evidence is stored.",
        )
    if item.status == "approved":
        return (
            "Approved; ready for handoff",
            "No Accounting handoff has been evidenced.",
        )
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


def _accounting_record(item: AccountingStatusFact) -> FinancialsRecordViewModel:
    delivery = item.delivery
    has_external_outcome = bool(item.latest_external_event_type)
    if has_external_outcome:
        status_label = _humanize(
            item.latest_external_status or item.latest_external_event_type
        )
    elif item.delivery_requested_at is not None:
        status_label = "Local handoff requested"
    else:
        status_label = _humanize(item.preparation_status)
    external_reference = (
        item.latest_external_invoice_reference or item.latest_reconciliation_reference
    )
    transport_label = "No durable handoff"
    if delivery is not None:
        transport_label = {
            "pending": "Queued",
            "claimed": "Delivery in progress",
            "retry": "Retry scheduled",
            "published": "Transport delivered",
            "dead_letter": "Permanent transport failure",
        }.get(delivery.transport_state, "Transport state unavailable")
        if delivery.transport_state == "retry" and delivery.failure_category in {
            "configuration_blocked",
            "credential_failure",
        }:
            transport_label = "Blocked configuration"
    subtitle = "Transport: " + transport_label
    supporting = [
        "Accounting outcome: "
        + (status_label if has_external_outcome else "Not received"),
    ]
    if delivery is not None:
        supporting.extend(
            [
                f"Handoff: {delivery.handoff_id} | Approved version: {delivery.approved_source_version}",
                f"External destination: {delivery.adapter_id or 'Not pinned'} / {delivery.connection_id or 'Not pinned'}",
                f"Requested: {_timestamp(delivery.requested_at)} | Last activity: {_timestamp(delivery.last_activity_at)}",
                f"Attempts: {delivery.attempt_count} of {delivery.max_attempts}",
            ]
        )
        if delivery.next_attempt_at is not None:
            supporting.append(
                "Next automatic attempt: " + _timestamp(delivery.next_attempt_at)
            )
        if delivery.failure_category is not None:
            supporting.append(
                "Failure category: " + _humanize(delivery.failure_category)
            )
        if delivery.receipt_reference is not None:
            supporting.append("Transport reference: " + delivery.receipt_reference)
        if delivery.external_sequence is not None:
            supporting.append(
                f"Accepted external sequence: {delivery.external_sequence}"
            )
        if delivery.quarantined_count:
            supporting.append(
                f"Quarantined evidence: {delivery.quarantined_count} | Incident: {delivery.latest_quarantine_id} | Received: {_timestamp(delivery.latest_quarantine_at)}"
            )
            if delivery.latest_quarantine_reason is not None:
                supporting.append(
                    "Quarantine category: "
                    + _humanize(delivery.latest_quarantine_reason)
                )
    if external_reference:
        supporting.append("Accounting reference: " + external_reference)
    if item.handoff_unavailable_reason is not None:
        supporting.append("Handoff: " + _humanize(item.handoff_unavailable_reason))
    supporting.append(
        "Handoff requests are managed in Billing. Retries are automatic; manual retry is not supported."
    )
    supporting_text = "\n".join(supporting)
    occurred_at = item.latest_external_occurred_at or item.delivery_requested_at
    return FinancialsRecordViewModel(
        can_primary_action=False,
        can_secondary_action=False,
        id=item.id,
        title=item.preparation_number,
        status_label=status_label,
        subtitle=subtitle,
        supporting_text=supporting_text,
        meta_text=occurred_at.isoformat() if occurred_at is not None else "",
        state={
            "canViewAccountingStatus": True,
            "canRequestAccountingHandoff": item.can_request_accounting_handoff,
            "handoffUnavailableReason": item.handoff_unavailable_reason,
            "canRetryAccountingHandoff": item.can_retry_accounting_handoff,
            "retryUnavailableReason": item.retry_unavailable_reason,
            "handoffId": delivery.handoff_id if delivery is not None else None,
            "approvedSourceVersion": delivery.approved_source_version
            if delivery is not None
            else None,
            "transportState": delivery.transport_state
            if delivery is not None
            else None,
            "transportLabel": transport_label,
            "attemptCount": delivery.attempt_count if delivery is not None else None,
            "nextAttemptAt": _timestamp(delivery.next_attempt_at)
            if delivery is not None
            else None,
            "failureCategory": delivery.failure_category
            if delivery is not None
            else None,
            "quarantinedCount": delivery.quarantined_count
            if delivery is not None
            else None,
            "latestQuarantineId": delivery.latest_quarantine_id
            if delivery is not None
            else None,
            "latestQuarantineReason": delivery.latest_quarantine_reason
            if delivery is not None
            else None,
            "externalSequence": delivery.external_sequence
            if delivery is not None
            else None,
            "preparationStatus": item.preparation_status,
            "deliveryRequestedLocally": item.delivery_requested_at is not None,
            "externalOutcomeRecorded": has_external_outcome,
            "externalEventType": item.latest_external_event_type,
            "externalSystem": item.latest_external_system,
            "externalStatus": item.latest_external_status,
            "externalReference": external_reference,
            "correctionOfPreparationId": item.correction_of_preparation_id or "",
            "correctionOfPreparationNumber": item.correction_of_preparation_number,
        },
    )


def _timestamp(value) -> str:
    return value.isoformat() if value is not None else ""


def _humanize(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


__all__ = ["build_accounting_status_collection", "build_billing_workspace_views"]
