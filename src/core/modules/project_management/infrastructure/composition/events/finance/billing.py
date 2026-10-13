from __future__ import annotations

from src.core.modules.project_management.application.financials.invoicing.billing_events import (
    AccountingTransportFinalized,
    BillingPreparationCreated,
    BillingPreparationExternalOutcomeRecorded,
    BillingPreparationLineAdded,
    BillingPreparationLineRemoved,
    BillingPreparationStatusChanged,
    BillingProfileActivated,
    BillingProfileCreated,
    BillingScheduleLineAdded,
    BillingScheduleLineMarkedReady,
)
from src.core.modules.project_management.application.financials.invoicing.event_handlers.view_invalidation import (
    build_billing_view_invalidation_handler,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_billing_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_billing_view_invalidation_handler(view_channel)
    for event_type in (
        AccountingTransportFinalized,
        BillingProfileCreated,
        BillingProfileActivated,
        BillingScheduleLineAdded,
        BillingScheduleLineMarkedReady,
        BillingPreparationCreated,
        BillingPreparationLineAdded,
        BillingPreparationLineRemoved,
        BillingPreparationStatusChanged,
        BillingPreparationExternalOutcomeRecorded,
    ):
        post_commit_bus.subscribe(event_type, handler)
