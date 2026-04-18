from __future__ import annotations

import pytest

from src.core.platform.common.exceptions import ValidationError
from tests.ui_runtime_helpers import login_as, wait_until
from ui.modules.project_management.collaboration.tab import CollaborationTab
from ui.modules.project_management.task.collaboration_dialog import TaskCollaborationDialog


def test_collaboration_service_lists_project_candidates_and_resolves_user_mentions(services):
    auth = services["auth_service"]
    access = services["access_service"]
    project_service = services["project_service"]
    task_service = services["task_service"]
    collaboration = services["collaboration_service"]

    project = project_service.create_project("Mention Candidates Project")
    task = task_service.create_task(project.id, "Mention Candidate Task")
    viewer = auth.register_user("mention-viewer", "StrongPass123", role_names=["viewer"])
    outsider = auth.register_user("mention-outsider", "StrongPass123", role_names=["viewer"])
    access.assign_project_membership(project_id=project.id, user_id=viewer.id, scope_role="viewer")

    candidates = collaboration.list_mention_candidates(task.id)

    assert {candidate.handle for candidate in candidates} >= {"mention-viewer"}
    assert "mention-outsider" not in {candidate.handle for candidate in candidates}

    comment = collaboration.post_comment(task_id=task.id, body="Please review @mention-viewer")

    assert comment.mentions == ["mention-viewer"]
    assert comment.mentioned_user_ids == [viewer.id]


def test_collaboration_service_rejects_unknown_mentions(services):
    project = services["project_service"].create_project("Unknown Mentions Project")
    task = services["task_service"].create_task(project.id, "Unknown Mention Task")

    with pytest.raises(ValidationError, match="Unknown mention handle"):
        services["collaboration_service"].post_comment(task_id=task.id, body="Please review @nobody")


def test_task_collaboration_dialog_uses_service_backed_mentions_runtime(qapp, services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Dialog Mention Project")
    task = services["task_service"].create_task(project.id, "Dialog Mention Task")
    viewer = auth.register_user("dialog-viewer", "StrongPass123", role_names=["viewer"])
    access.assign_project_membership(project_id=project.id, user_id=viewer.id, scope_role="viewer")

    dialog = TaskCollaborationDialog(
        None,
        collaboration_service=services["collaboration_service"],
        task_id=task.id,
        task_name=task.name,
        username="admin",
        mention_aliases=["admin"],
    )

    assert dialog.mention_combo.count() >= 2
    dialog.mention_combo.setCurrentIndex(dialog.mention_combo.findData("dialog-viewer"))
    dialog._insert_selected_mention()
    assert "@dialog-viewer" in dialog.comment_input.toPlainText()

    dialog.comment_input.setPlainText("Please review @dialog-viewer")
    dialog._post_comment()

    comments = services["collaboration_service"].list_comments(task.id)
    assert len(comments) == 1
    assert comments[0].mentioned_user_ids == [viewer.id]


def test_collaboration_tab_shows_mentions_column_and_unread_state_runtime(qapp, services):
    auth = services["auth_service"]
    access = services["access_service"]
    project = services["project_service"].create_project("Inbox Mention Project")
    task = services["task_service"].create_task(project.id, "Inbox Mention Task")
    viewer = auth.register_user("inbox-viewer", "StrongPass123", role_names=["viewer"])
    access.assign_project_membership(project_id=project.id, user_id=viewer.id, scope_role="viewer")
    services["collaboration_service"].post_comment(task_id=task.id, body="Please review @inbox-viewer")

    login_as(services, "inbox-viewer", "StrongPass123")

    tab = CollaborationTab(collaboration_service=services["collaboration_service"])
    wait_until(qapp, lambda: tab.inbox_table.rowCount() == 1)

    assert tab.inbox_table.columnCount() == 6
    assert tab.inbox_table.item(0, 4).text() == "@inbox-viewer"
    assert tab.inbox_table.item(0, 0).font().bold() is True
