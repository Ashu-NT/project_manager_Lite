from importlib import import_module
from types import SimpleNamespace

import pytest

from src.core.modules.project_management.api.desktop.collaboration.api import ProjectManagementCollaborationDesktopApi
from src.core.modules.project_management.application.collaboration.dto.commands.task_comments import TaskCollaborationPostCommand
from src.core.modules.project_management.application.collaboration.dto.responses.comments import TaskCommentResponseDto
from src.core.modules.project_management.contracts.reads.collaboration.models.workspace_facts import TaskDetailCommentFact, TaskDetailCommentReadPage
from src.ui_qml.modules.project_management.presenters.tasks.collaboration_builder import build_task_collaboration_state


@pytest.mark.parametrize("module_name", [
    "_pm_task_service_helpers",
    "_task_presenters_test_helpers",
    "_task_presenter_test_helpers",
    "_helpers_pm_presenters_base",
    "test_qml_project_management_presenters_tasks_bulk",
])
def test_collaboration_fake_uses_canonical_command_and_read_contracts(module_name):
    module = import_module(f"src.tests.ui_qml.project_management.presenters.{module_name}")
    fake = module._FakeCollaborationService()
    command = TaskCollaborationPostCommand(task_id="task-1", body="Canonical fake")
    result = fake.post_comment(command)
    assert isinstance(result, TaskCommentResponseDto)
    page = fake.query_task_comments_page("task-1")
    assert isinstance(page, TaskDetailCommentReadPage)
    assert all(isinstance(item, TaskDetailCommentFact) for item in page.items)
    api = ProjectManagementCollaborationDesktopApi(comment_query=fake, document_query=fake, presence_query=fake)
    view = build_task_collaboration_state(SimpleNamespace(get_task=lambda task_id: object()), api, task_id="task-1")
    assert any(item.subtitle == command.body for item in view.collaboration_comments.items)
