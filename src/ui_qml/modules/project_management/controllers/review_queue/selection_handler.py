from __future__ import annotations

from .filter_normalization import normalize_queue_status


def set_queue_status(controller, queue_status: str) -> None:
    normalized = normalize_queue_status(queue_status)
    if normalized != controller._selected_queue_status:
        controller._set_selected_queue_status(normalized)
        controller._set_selected_queue_period_id("")
        controller._set_queue_page(1)
        controller.refresh()


__all__ = ["set_queue_status"]
