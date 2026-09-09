from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.runtime import build_desktop_api_registry
from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)


def _controller(services):
    registry = build_desktop_api_registry(services)
    catalog = ProjectManagementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.financialsWorkspace
    controller._test_catalog_owner = catalog
    return controller


def test_scoped_task_schedule_stale_invalidates_only_dependent_destinations(services) -> None:
    """Scoped Task-schedule invalidation must invalidate only the dependent finance
    destinations, not all of them."""
    controller = _controller(services)
    project_id = "r6b-invalidation-project"
    expected = {"planning", "costs", "performance"}
    controller._set_selected_project_id(project_id)
    controller._active_destination = "unrelated"
    controller._invalidated_destinations.clear()
    controller._loaded_destination_keys = {
        (project_id, destination, "test")
        for destination in controller._finance_destinations
    }
    controller._request_domain_refresh = MagicMock()

    controller.onTaskScheduleStale(project_id)

    assert controller._invalidated_destinations == expected
    assert {key[1] for key in controller._loaded_destination_keys}.isdisjoint(expected)
    assert {key[1] for key in controller._loaded_destination_keys} == (
        set(controller._finance_destinations) - expected
    )
    controller._request_domain_refresh.assert_not_called()


def test_finance_invalidation_rejects_other_project(services) -> None:
    """`onTaskScheduleStale` only checks project-id equality -- an event for a different
    project must be rejected."""
    controller = _controller(services)
    controller._set_selected_project_id("selected-project")
    controller._invalidated_destinations.clear()
    controller._request_domain_refresh = MagicMock()

    controller.onTaskScheduleStale("other-project")

    assert controller._invalidated_destinations == set()
    controller._request_domain_refresh.assert_not_called()


def test_finance_refresh_does_not_reemit_business_invalidation(services, qapp) -> None:
    """Calling `onTaskScheduleStale` for the active destination must trigger exactly one
    deferred, timer-scheduled refresh."""
    controller = _controller(services)
    controller._set_selected_project_id("selected-project")
    controller._active_destination = "planning"
    refreshes: list[str] = []
    controller.refresh = lambda: refreshes.append("refresh")

    controller.onTaskScheduleStale("selected-project")
    qapp.processEvents()

    assert refreshes == ["refresh"]
