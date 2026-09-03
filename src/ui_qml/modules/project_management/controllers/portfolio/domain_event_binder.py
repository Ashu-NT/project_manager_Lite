from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QCoreApplication

from src.core.shared.events.domain_events import domain_events

logger = logging.getLogger(__name__)


def bind_portfolio_domain_events(controller: object) -> None:

    def _on_domain_event(_payload: object) -> None:
        controller._request_domain_refresh()

    for signal in (
        domain_events.project_changed,
        domain_events.tasks_changed,
    ):
        controller._subscribe_domain_signal(signal, _on_domain_event)


def portfolio_request_domain_refresh(
    controller: object,
    fallback_refresh: Callable,
) -> None:
    if QCoreApplication.instance() is None:
        fallback_refresh()
        return
    controller._pending_domain_refresh = True
    if controller._is_loading or controller._is_busy:
        logger.debug("PM portfolio domain refresh queued while busy/loading")
        return
    if controller._domain_refresh_scheduled:
        logger.debug("PM portfolio domain refresh coalesced; refresh already scheduled")
        return
    controller._domain_refresh_scheduled = True
    logger.debug("PM portfolio domain refresh scheduled")
    controller._domain_refresh_timer.start(0)


__all__ = ["bind_portfolio_domain_events", "portfolio_request_domain_refresh"]
