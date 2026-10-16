"""Projects API returns application/Reader results without presentation copies."""

from dataclasses import replace
from decimal import Decimal
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.projects.api import (
    ProjectManagementProjectsDesktopApi,
)
from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.contracts.reads.projects.models import (
    ProjectActivityPage,
    ProjectCatalogReadPage,
    ProjectResourceDetailPage,
)
from src.ui_qml.modules.project_management.presenters.projects.project_mapper import (
    build_project_state,
)


@pytest.mark.parametrize(
    ("api_method", "query_method", "page", "args"),
    [
        ("list_project_page", "query_catalog_page", ProjectCatalogReadPage(), ()),
        (
            "list_project_resources_page",
            "query_project_resources_page",
            ProjectResourceDetailPage(),
            ("project",),
        ),
        (
            "list_project_activity_page",
            "query_project_activity_page",
            ProjectActivityPage(),
            ("project",),
        ),
    ],
)
def test_project_api_preserves_canonical_page_identity(
    api_method, query_method, page, args
):
    query = Mock()
    getattr(query, query_method).return_value = page
    api = ProjectManagementProjectsDesktopApi(project_query=query)
    assert getattr(api, api_method)(*args) is page


def test_project_commands_return_original_results_and_do_not_reload(services):
    command = ProjectCreateCommand(name="Vertical boundary", status="ACTIVE")
    response = services["project_create"].create_project(command)
    create = Mock()
    create.create_project.return_value = response
    status = Mock()
    status.set_status.return_value = response
    status.bulk_set_status.return_value = [response]
    query = Mock()
    api = ProjectManagementProjectsDesktopApi(
        project_create=create, project_status=status, project_query=query
    )
    assert api.create_project(command) is response
    create.create_project.assert_called_once_with(command)
    assert api.set_project_status(response.id, "ACTIVE") is response
    assert api.bulk_set_project_status((response.id,), "ACTIVE")[0] is response
    assert query.mock_calls == []


def test_project_presentation_preserves_available_zero_and_redaction(services):
    response = services["project_create"].create_project(
        ProjectCreateCommand(name="Budget DTO")
    )
    available = replace(
        response,
        approved_budget=Decimal("0.00"),
        approved_budget_visible=True,
        approved_budget_currency="EUR",
    )
    state = build_project_state(available)
    assert state["approvedBudgetVisible"] is True
    assert Decimal(state["approvedBudget"]) == Decimal(0)
    assert state["approvedBudgetLabel"] == "EUR 0.00"
    hidden = replace(
        response,
        approved_budget=None,
        approved_budget_visible=False,
        approved_budget_currency="",
    )
    state = build_project_state(hidden)
    assert state["approvedBudgetVisible"] is False
    assert (
        state["approvedBudget"]
        == state["approvedBudgetLabel"]
        == state["approvedBudgetCurrency"]
        == ""
    )
