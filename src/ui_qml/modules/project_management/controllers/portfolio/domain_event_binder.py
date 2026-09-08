from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import QCoreApplication

logger = logging.getLogger(__name__)


def on_task_metrics_stale(controller: object, _project_id: str) -> None:
    """Portfolio Executive/heatmap computes real per-project critical/late
    task counts from Task status/schedule/dependency/removal facts (P45A) --
    `taskListStale` already covers Created/StatusChanged/ScheduleChanged/
    HierarchyChanged/Removed; `taskDependenciesStale` covers the one fact
    `taskListStale` doesn't (a dependency add/update/remove can move a task
    in or out of "late" without the task's own row changing). Neither
    TaskProfileUpdated-only nor TaskProgressChanged-only changes reach here
    via a distinct signal, so this remains a modest over-trigger versus a
    theoretical maximally-precise mapping -- still a real, disclosed
    improvement over the previous blanket-every-Task-fact refresh."""
    controller._request_domain_refresh()


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


__all__ = ["on_task_metrics_stale", "portfolio_request_domain_refresh"]
