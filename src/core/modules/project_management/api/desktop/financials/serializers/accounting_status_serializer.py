from __future__ import annotations

from src.core.modules.project_management.api.desktop.financials.models.billing_workspace import (
    FinancialAccountingStatusPageDto,
    FinancialBillingTableRecordDto,
)


def serialize_accounting_status_page(page) -> FinancialAccountingStatusPageDto:
    return FinancialAccountingStatusPageDto(
        items=tuple(_serialize_row(item) for item in page.items),
        total=page.total,
        page=page.page,
        page_size=page.page_size,
        sort_key=page.sort_key,
        sort_direction=page.sort_direction,
    )


def _serialize_row(item) -> FinancialBillingTableRecordDto:
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
        item.latest_external_invoice_reference
        or item.latest_reconciliation_reference
    )
    transport_label = "No durable handoff"
    if delivery is not None:
        transport_label = {
            "pending": "Queued", "claimed": "Delivery in progress",
            "retry": "Retry scheduled", "published": "Transport delivered",
            "dead_letter": "Permanent transport failure",
        }.get(delivery.transport_state, "Transport state unavailable")
        if (delivery.transport_state == "retry"
                and delivery.failure_category in {"configuration_blocked", "credential_failure"}):
            transport_label = "Blocked configuration"
    subtitle = "Transport: " + transport_label
    supporting = [
        "Accounting outcome: " + (status_label if has_external_outcome else "Not received"),
    ]
    if delivery is not None:
        supporting.extend([
            f"Handoff: {delivery.handoff_id} | Approved version: {delivery.approved_source_version}",
            f"External destination: {delivery.adapter_id or 'Not pinned'} / {delivery.connection_id or 'Not pinned'}",
            f"Requested: {_timestamp(delivery.requested_at)} | Last activity: {_timestamp(delivery.last_activity_at)}",
            f"Attempts: {delivery.attempt_count} of {delivery.max_attempts}",
        ])
        if delivery.next_attempt_at is not None:
            supporting.append("Next automatic attempt: " + _timestamp(delivery.next_attempt_at))
        if delivery.failure_category is not None:
            supporting.append("Failure category: " + _humanize(delivery.failure_category))
        if delivery.receipt_reference is not None:
            supporting.append("Transport reference: " + delivery.receipt_reference)
        if delivery.external_sequence is not None:
            supporting.append(f"Accepted external sequence: {delivery.external_sequence}")
        if delivery.quarantined_count:
            supporting.append(
                f"Quarantined evidence: {delivery.quarantined_count} | Incident: {delivery.latest_quarantine_id} | Received: {_timestamp(delivery.latest_quarantine_at)}"
            )
            if delivery.latest_quarantine_reason is not None:
                supporting.append("Quarantine category: " + _humanize(delivery.latest_quarantine_reason))
    if external_reference:
        supporting.append("Accounting reference: " + external_reference)
    if item.handoff_unavailable_reason is not None:
        supporting.append("Handoff: " + _humanize(item.handoff_unavailable_reason))
    supporting.append("Handoff requests are managed in Billing. Retries are automatic; manual retry is not supported.")
    supporting_text = "\n".join(supporting)
    occurred_at = item.latest_external_occurred_at or item.delivery_requested_at
    return FinancialBillingTableRecordDto(
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
            "approvedSourceVersion": delivery.approved_source_version if delivery is not None else None,
            "transportState": delivery.transport_state if delivery is not None else None,
            "transportLabel": transport_label,
            "attemptCount": delivery.attempt_count if delivery is not None else None,
            "nextAttemptAt": _timestamp(delivery.next_attempt_at) if delivery is not None else None,
            "failureCategory": delivery.failure_category if delivery is not None else None,
            "quarantinedCount": delivery.quarantined_count if delivery is not None else None,
            "latestQuarantineId": delivery.latest_quarantine_id if delivery is not None else None,
            "latestQuarantineReason": delivery.latest_quarantine_reason if delivery is not None else None,
            "externalSequence": delivery.external_sequence if delivery is not None else None,
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


__all__ = ["serialize_accounting_status_page"]
