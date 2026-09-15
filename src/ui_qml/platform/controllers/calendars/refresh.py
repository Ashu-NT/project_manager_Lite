from __future__ import annotations

from src.ui_qml.platform.controllers.overview.refresh_coordinator import (
    refresh_empty_state,
)


def refresh_after_calendar_change(controller) -> None:
    controller._calendar_controller.refresh()
    refresh_empty_state(controller)


__all__ = ["refresh_after_calendar_change"]
