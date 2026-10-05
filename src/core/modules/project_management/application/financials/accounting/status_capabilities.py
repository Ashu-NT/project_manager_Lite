"""Page-level integration evaluation and row-level business eligibility."""

from dataclasses import replace

from src.core.platform.domain.integration.accounting.connector import (
    AccountingHandoffCapability,
    AccountingHandoffDenial,
)


def with_accounting_capabilities(page, *, capability_service, authorized):
    capability = (
        capability_service.evaluate(authorized=authorized, eligible=True)
        if capability_service is not None
        else AccountingHandoffCapability(
            allowed=False,
            reason=(
                AccountingHandoffDenial.ADAPTER_NOT_INSTALLED
                if authorized
                else AccountingHandoffDenial.PERMISSION_DENIED
            ),
        )
    )
    items = []
    for item in page.items:
        reason = capability.reason.value if capability.reason is not None else None
        if reason is None:
            if item.delivery is not None:
                reason = (
                    "handoff_already_terminal"
                    if item.delivery.transport_state in {"published", "dead_letter"}
                    else "handoff_already_in_progress"
                )
            elif not item.handoff_eligible:
                reason = AccountingHandoffDenial.BUSINESS_PRECONDITION_FAILED.value
        items.append(
            replace(
                item,
                can_request_accounting_handoff=reason is None,
                handoff_unavailable_reason=reason,
            )
        )
    return replace(page, items=tuple(items))
