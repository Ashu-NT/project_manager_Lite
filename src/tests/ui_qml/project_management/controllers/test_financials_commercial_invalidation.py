from __future__ import annotations

import pytest

from src.ui_qml.modules.project_management.controllers.financials.commitments.commitment_domain_event_binder import (
    on_commitment_stale,
)
from src.ui_qml.modules.project_management.controllers.financials.cost.cost_entry_domain_event_binder import (
    on_cost_entry_actuals_stale,
)
from src.ui_qml.modules.project_management.controllers.financials.forecasts.forecast_domain_event_binder import (
    on_forecast_approved_basis_stale,
)
from src.ui_qml.modules.project_management.controllers.financials.governance.financial_setup_domain_event_binder import (
    on_financial_profile_stale,
)
from src.ui_qml.modules.project_management.controllers.financials.invoicing.billing_domain_event_binder import (
    on_billing_commercial_stale,
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


@pytest.mark.parametrize("handler", [on_cost_entry_actuals_stale, on_forecast_approved_basis_stale,
                                      on_billing_commercial_stale, on_commitment_stale])
def test_commercial_dependencies_invalidate_only_matching_project(handler):
    controller = _Controller()
    handler(controller, "project-b")
    assert controller.invalidated == []
    handler(controller, "project-a")
    assert len(controller.invalidated) == 1
    assert "commercial" in controller.invalidated[0]
