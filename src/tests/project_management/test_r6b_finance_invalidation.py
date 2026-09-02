from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.modules.project_management.application.financials.invalidation import (
    FinanceInvalidationScope,
)
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)


def _controller(services):
    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.financialsWorkspace
    controller._test_catalog_owner = catalog
    return controller


@pytest.mark.parametrize(
    ("signal_name", "expected"),
    (
        ("cost_entries_changed", {"overview", "costs", "performance", "commercial"}),
        ("commitments_changed", {"overview", "planning", "costs", "performance", "commercial"}),
    ),
)
def test_scoped_finance_events_invalidate_only_dependent_destinations(
    services, signal_name: str, expected: set[str]
) -> None:
    controller = _controller(services)
    project_id = "r6b-invalidation-project"
    controller._set_selected_project_id(project_id)
    controller._active_destination = "unrelated"
    controller._invalidated_destinations.clear()
    controller._loaded_destination_keys = {
        (project_id, destination, "test")
        for destination in controller._finance_destinations
    }
    controller._request_domain_refresh = MagicMock()

    signal = getattr(domain_events, signal_name)
    signal.emit(
        FinanceInvalidationScope(
            tenant_id=controller._active_tenant_id,
            organization_id=controller._active_organization_id,
            project_id=project_id,
        )
    )

    assert controller._invalidated_destinations == expected
    assert {key[1] for key in controller._loaded_destination_keys}.isdisjoint(expected)
    assert {key[1] for key in controller._loaded_destination_keys} == (
        set(controller._finance_destinations) - expected
    )
    controller._request_domain_refresh.assert_not_called()
    controller._disconnect_domain_event_subscriptions()


def test_finance_invalidation_rejects_other_project_and_organization(services) -> None:
    controller = _controller(services)
    controller._set_selected_project_id("selected-project")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = MagicMock()

    domain_events.commitments_changed.emit(
        FinanceInvalidationScope(
            tenant_id=controller._active_tenant_id,
            organization_id=controller._active_organization_id,
            project_id="other-project",
        )
    )
    domain_events.commitments_changed.emit(
        FinanceInvalidationScope(
            tenant_id=controller._active_tenant_id,
            organization_id="other-organization",
            project_id="selected-project",
        )
    )

    assert controller._invalidated_destinations == set()
    controller._request_domain_refresh.assert_not_called()
    controller._disconnect_domain_event_subscriptions()


def test_finance_controller_teardown_and_reopen_do_not_accumulate_subscriptions(
    services,
) -> None:
    signal = domain_events.commitments_changed
    baseline = len(signal._subscribers)

    first = _controller(services)
    assert len(signal._subscribers) == baseline + 1
    first._disconnect_domain_event_subscriptions()
    assert len(signal._subscribers) == baseline

    second = _controller(services)
    assert len(signal._subscribers) == baseline + 1
    second._disconnect_domain_event_subscriptions()
    assert len(signal._subscribers) == baseline


def test_finance_refresh_does_not_reemit_business_invalidation(services, qapp) -> None:
    controller = _controller(services)
    controller._set_selected_project_id("selected-project")
    controller._active_destination = "overview"
    refreshes: list[str] = []
    observed: list[FinanceInvalidationScope] = []
    controller.refresh = lambda: refreshes.append("refresh")

    def capture(scope: FinanceInvalidationScope) -> None:
        observed.append(scope)

    domain_events.commitments_changed.connect(capture)
    try:
        domain_events.commitments_changed.emit(
            FinanceInvalidationScope(
                tenant_id=controller._active_tenant_id,
                organization_id=controller._active_organization_id,
                project_id="selected-project",
            )
        )
        qapp.processEvents()
    finally:
        domain_events.commitments_changed.disconnect(capture)
        controller._disconnect_domain_event_subscriptions()

    assert refreshes == ["refresh"]
    assert len(observed) == 1
