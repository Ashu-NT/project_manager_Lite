from __future__ import annotations

from src.core.modules.project_management.application.financials.forecasts.event_handlers.view_invalidation import (
    build_forecast_view_invalidation_handler,
)
from src.core.modules.project_management.application.financials.forecasts.forecast_events import (
    ForecastDraftGenerated,
    ForecastLineChanged,
    ForecastVersionChanged,
)
from src.core.shared.events.view_invalidation import ViewInvalidationChannel
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)


def register_forecast_view_invalidation(
    post_commit_bus: InProcessPostCommitEventBus,
    view_channel: ViewInvalidationChannel,
) -> None:
    handler = build_forecast_view_invalidation_handler(view_channel)
    for event_type in (ForecastVersionChanged, ForecastLineChanged, ForecastDraftGenerated):
        post_commit_bus.subscribe(event_type, handler)
