from __future__ import annotations

from src.ui_qml.modules.project_management.controllers.financials.financial_setup_domain_event_binder import (
    on_financial_profile_stale,
)


class _Controller:
    _selected_project_id = "project-a"

    def __init__(self) -> None:
        self.invalidated: list[tuple[str, ...]] = []

    def _invalidate_destinations(self, *destinations: str) -> None:
        self.invalidated.append(destinations)


def test_financial_profile_change_invalidates_only_selected_project_controls_and_commercial() -> None:
    controller = _Controller()
    on_financial_profile_stale(controller, "project-b")
    assert controller.invalidated == []

    on_financial_profile_stale(controller, "project-a")
    assert controller.invalidated == [("controls", "commercial")]
