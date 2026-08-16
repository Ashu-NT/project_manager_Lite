from __future__ import annotations

from src.ui_qml.platform.controllers.admin_console.refresh_coordinator import (
    refresh_empty_state,
    refresh_overview,
)


def refresh_after_party_change(controller) -> None:
    refresh_overview(controller)
    refresh_empty_state(controller)


__all__ = ["refresh_after_party_change"]
