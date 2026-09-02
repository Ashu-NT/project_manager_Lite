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
    subtitle = item.latest_external_system or "No external Accounting outcome"
    supporting_text = external_reference or item.latest_external_message
    occurred_at = item.latest_external_occurred_at or item.delivery_requested_at
    return FinancialBillingTableRecordDto(
        id=item.id,
        title=item.preparation_number,
        status_label=status_label,
        subtitle=subtitle,
        supporting_text=supporting_text,
        meta_text=occurred_at.isoformat() if occurred_at is not None else "",
        state={
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


def _humanize(value: str) -> str:
    return str(value or "").replace("_", " ").strip().title()


__all__ = ["serialize_accounting_status_page"]
