from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.api.desktop.collaboration.api import (
    ProjectManagementCollaborationDesktopApi,
)
from src.core.modules.project_management.api.desktop.resources.api import (
    ProjectManagementResourcesDesktopApi,
)
from src.core.modules.project_management.application.collaboration.dto.commands.comment_reactions import (
    TaskCollaborationReactionCommand,
)
from src.core.modules.project_management.application.collaboration.dto.commands.task_comments import (
    TaskCollaborationDeleteCommand,
    TaskCollaborationEditCommand,
    TaskCollaborationPostCommand,
)
from src.core.modules.project_management.application.resources.dto.responses.availability import (
    ResourceWorkloadDayResponse,
    ResourceWorkloadResponse,
)
from src.core.modules.project_management.application.tasks.dto.commands.task_lifecycle import (
    TaskCreateCommand,
)
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import (
    TaskDetailCommentReadPage,
)
from src.core.modules.project_management.contracts.reads.resources.models import (
    ResourceCatalogReadItem,
    ResourceCatalogReadPage,
    ResourceInspectorFact,
    ResourceSummaryFact,
)
from src.tests.project_management.api.test_project_management_desktop_api_workspace_collaboration import (
    _FakeCollaborationService,
)
from src.ui_qml.modules.project_management.presenters.resources.availability_builder import (
    build_resource_availability_state,
)
from src.ui_qml.modules.project_management.presenters.resources.detail_builder import (
    build_resource_state,
)
from src.ui_qml.modules.project_management.presenters.resources.resource_mapper import (
    to_resource_record_view_model,
)
from src.ui_qml.modules.project_management.presenters.tasks.collaboration_builder import (
    build_task_collaboration_state,
)


def _assert_immutable_neutral_fact(value):
    if value is None or isinstance(value, (str, bool, int, float, Decimal, date, datetime, Enum)):
        return
    if isinstance(value, tuple):
        for item in value:
            _assert_immutable_neutral_fact(item)
        return
    assert is_dataclass(value), type(value)
    assert value.__dataclass_params__.frozen, type(value)
    assert ".domain." not in type(value).__module__, type(value)
    for field in fields(value):
        _assert_immutable_neutral_fact(getattr(value, field.name))


def test_resource_reads_keep_identity_and_zero_values():
    query = Mock()
    item = ResourceCatalogReadItem(
        "r", "R", "Resource", "", "EXTERNAL", "LABOR", True, 0, "org"
    )
    page = ResourceCatalogReadPage(items=(item,))
    inspector = ResourceInspectorFact(
        "r", "R", "Resource", "", "EXTERNAL", True, 0, "org", can_manage=True
    )
    summary = ResourceSummaryFact(
        "r",
        "R",
        "Resource",
        "",
        "EXTERNAL",
        "LABOR",
        Decimal("0.00"),
        None,
        True,
        0,
        "",
        "",
        "org",
    )
    query.query_catalog_page.return_value = page
    query.get_resource_inspector.return_value = inspector
    query.get_resource_summary.return_value = summary
    api = ProjectManagementResourcesDesktopApi(resource_query=query)
    assert api.list_resource_page() is page
    assert api.get_resource_inspector("r") is inspector
    assert api.get_resource_summary("r") is summary
    for fact in (page, inspector, summary):
        _assert_immutable_neutral_fact(fact)
    assert to_resource_record_view_model(item).state["capacityPercent"] == 0
    state = build_resource_state(summary)
    assert state["hourlyRate"] == "0"
    assert state["currency"] == ""
    assert state["capacityPercent"] == "0.0"


@pytest.mark.parametrize("utilization", [None, Decimal(0)])
def test_workload_preserves_decimal_none_and_zero_until_presenter(utilization):
    day = ResourceWorkloadDayResponse(
        date(2026, 1, 1),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        utilization,
        False,
        0,
    )
    response = ResourceWorkloadResponse(
        "r",
        day.work_date,
        day.work_date,
        (),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        utilization,
        False,
        (),
        0,
        0,
        1,
        (day,),
    )
    query = Mock()
    query.read.return_value = response
    api = ProjectManagementResourcesDesktopApi(workload_service=query)
    assert (
        api.build_resource_availability(
            "r", start_date="2026-01-01", end_date="2026-01-01"
        )
        is response
    )
    view = build_resource_availability_state(
        api, "r", start_date="2026-01-01", end_date="2026-01-01"
    )
    assert view.utilization_percent == utilization
    assert view.utilization_label == ("N/A" if utilization is None else "0.0%")
    assert view.days[0].utilization_label == view.utilization_label
    assert view.capacity_percent == 0


@pytest.mark.parametrize(
    "method, handler_method, command",
    [
        (
            "post_task_comment",
            "post_comment",
            TaskCollaborationPostCommand(task_id="t", body="Body"),
        ),
        (
            "edit_task_comment",
            "edit_comment",
            TaskCollaborationEditCommand(
                comment_id="c", body="Edit", expected_revision=1
            ),
        ),
        (
            "delete_task_comment",
            "delete_comment",
            TaskCollaborationDeleteCommand(comment_id="c", expected_revision=1),
        ),
        (
            "react_to_task_comment",
            "react_to_comment",
            TaskCollaborationReactionCommand(comment_id="c", emoji="like"),
        ),
        (
            "remove_task_comment_reaction",
            "remove_reaction",
            TaskCollaborationReactionCommand(comment_id="c", emoji="like"),
        ),
    ],
)
def test_collaboration_commands_pass_identity_once(method, handler_method, command):
    handler = Mock()
    response = object()
    getattr(handler, handler_method).return_value = response
    api = ProjectManagementCollaborationDesktopApi(
        comment_commands=handler, comment_engagement=handler
    )
    assert getattr(api, method)(command) is response
    getattr(handler, handler_method).assert_called_once_with(command)


def test_snapshot_presenter_keeps_permissions_documents_replies_and_presence():
    service = _FakeCollaborationService()
    api = ProjectManagementCollaborationDesktopApi(
        comment_query=service, document_query=service, presence_query=service
    )
    task_api = SimpleNamespace(get_task=lambda task_id: object())
    view = build_task_collaboration_state(task_api, api, task_id="task-1")
    assert [option.value for option in view.collaboration_mention_options][:2] == [
        "everyone",
        "planner",
    ]
    assert (
        view.collaboration_document_options[0].label
        == "PM-LINK-001 - Shared Method Statement"
    )
    reply, parent = view.collaboration_comments.items
    assert reply.state["threadDepth"] == 1
    assert reply.state["canEdit"] is False
    assert parent.state["canEdit"] is True
    assert parent.state["reactions"][0]["reactedByCurrentUser"] is True
    assert parent.state["linkedDocuments"][0] == "procedure.pdf [General | File]"
    assert view.collaboration_presence.items[0].title == "Alex Taylor (@planner)"


def test_composed_comment_reader_page_is_not_copied(services, monkeypatch):
    query = services["collaboration_comment_query"]
    reader = query._workspace_reader
    captured = []
    original = reader.read_task_comment_page

    def read(**kwargs):
        result = original(**kwargs)
        captured.append(result)
        return result

    from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
        ProjectCreateCommand,
    )

    project = services["project_create"].create_project(
        ProjectCreateCommand(name="Canonical discussion")
    )
    task = services["task_lifecycle_commands"].create_task(
        TaskCreateCommand(project_id=project.id, name="Discuss")
    )
    services["collaboration_comment_commands"].post_comment(
        TaskCollaborationPostCommand(task_id=task.id, body="Populated neutral fact")
    )
    monkeypatch.setattr(reader, "read_task_comment_page", read)
    result = query.query_task_comments_page(task.id)
    assert isinstance(result, TaskDetailCommentReadPage)
    assert result is captured[0]
    assert len(result.items) == 1
    _assert_immutable_neutral_fact(result)
