"""Characterize existing fan-out; replace with bounded-query proof in R7D."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
)
from src.core.modules.project_management.application.global_overview.pm_action_center_contributor import (
    ProjectManagementActionCenterContributor,
)


@pytest.mark.parametrize("project_count", [5, 50])
def test_baseline_discovery_currently_calls_service_once_per_visible_project(
    project_count,
):
    baselines = Mock()
    baselines.list_baselines.return_value = []
    session = Mock()
    session.has_project_permission.return_value = True
    contributor = ProjectManagementActionCenterContributor(
        task_service=Mock(),
        baseline_service=baselines,
        project_service=Mock(),
        resource_identity_reader=Mock(),
        timesheet_workspace_reader=Mock(),
        user_session=session,
    )
    items = contributor._collect_baselines(
        ActionCenterContext(user_id="user", tenant_id="tenant", organization_id="org"),
        [SimpleNamespace(id=f"project-{index}") for index in range(project_count)],
    )
    assert items == ()
    assert baselines.list_baselines.call_count == project_count
