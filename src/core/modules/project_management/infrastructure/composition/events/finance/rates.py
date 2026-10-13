from __future__ import annotations

from src.core.modules.project_management.application.financials.rate_cards.event_handlers.view_invalidation import (
    build_rate_card_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.rate_cards.rate_card_events import (
    RateCardCreated,
    RateCardDeactivated,
    RateCardLineAdded,
    RateCardLineDeactivated,
    RateCardLineUpdated,
    RateCardUpdated,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_rate_card_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_rate_card_view_invalidation_handler(view_channel)
    for event_type in (
        RateCardCreated,
        RateCardDeactivated,
        RateCardUpdated,
        RateCardLineAdded,
        RateCardLineUpdated,
        RateCardLineDeactivated,
    ):
        post_commit_bus.subscribe(event_type, handler)
