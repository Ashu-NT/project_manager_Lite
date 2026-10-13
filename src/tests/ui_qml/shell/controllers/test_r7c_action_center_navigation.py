from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.ui_qml.shell.global_overview_navigation import navigate_action


@pytest.mark.parametrize("kind,destination", [("pm_task", "tasks"), ("baseline_review", "scheduling"), ("timesheet", "timesheets")])
def test_pm_actions_use_canonical_module_and_do_not_pin_project(kind, destination):
    shell, navigation, platform = Mock(), Mock(), Mock()
    navigate_action({"routeId": "project_management.workspace", "destinationId": destination,
                     "kind": kind, "id": "object"}, shell_context=shell,
                    platform_catalog=platform, pm_catalog=SimpleNamespace(pmNavigation=navigation))
    shell.selectRoute.assert_called_once_with("project_management.workspace")
    platform.selectDestination.assert_not_called()
    if kind == "pm_task":
        navigation.openEntity.assert_called_once_with("tasks", "object", "")
    else:
        navigation.selectWorkspace.assert_called_once_with(destination)
        navigation.openEntity.assert_not_called()


def test_approval_enters_existing_platform_workflow_and_retired_routes_are_ignored():
    shell, platform, pm = Mock(), Mock(), Mock()
    navigate_action({"routeId": "platform.workspace", "destinationId": "control_approvals"},
                    shell_context=shell, platform_catalog=platform, pm_catalog=pm)
    platform.selectDestination.assert_called_once_with("control_approvals")
    shell.selectRoute.assert_called_once_with("platform.workspace")
    shell.reset_mock()
    navigate_action({"routeId": "project_management.tasks", "destinationId": "tasks"},
                    shell_context=shell, platform_catalog=platform, pm_catalog=pm)
    shell.selectRoute.assert_not_called()
