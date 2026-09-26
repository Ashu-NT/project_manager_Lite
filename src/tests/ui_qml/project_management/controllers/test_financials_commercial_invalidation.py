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


@pytest.mark.parametrize("active,refresh", [("profitability", False), ("billing", True), ("accounting", True)])
def test_transport_only_invalidates_billing_and_accounting(active, refresh):
    from types import SimpleNamespace
    from unittest.mock import Mock

    from src.ui_qml.modules.project_management.controllers.financials.financials_workspace_controller import (
        ProjectManagementFinancialsWorkspaceController,
    )

    keys = {("project-a", "commercial", item) for item in ("profitability", "billing", "accounting")}
    controller = SimpleNamespace(_selected_project_id="project-a", _loaded_destination_keys=keys.copy(),
        _active_destination="commercial", _active_subsection=active, _request_domain_refresh=Mock())
    handler = ProjectManagementFinancialsWorkspaceController.onBillingTransportStale
    handler(controller, "project-b")
    assert controller._loaded_destination_keys == keys
    handler(controller, "project-a")
    assert controller._loaded_destination_keys == {("project-a", "commercial", "profitability")}
    assert controller._request_domain_refresh.called is refresh
