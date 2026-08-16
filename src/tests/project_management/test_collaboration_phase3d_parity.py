from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.modules.project_management.contracts.reads.collaboration import (
    CollaborationCommentCriteria,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskPresenceORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration import (
    SqlAlchemyCollaborationWorkspaceReader,
)
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


def test_purpose_queries_preserve_mentions_recent_activity_and_presence(services) -> None:
    projects = services["project_service"]
    tasks = services["task_service"]
    collaboration = services["collaboration_service"]
    project = projects.create_project("Collaboration projection")
    task = tasks.create_task(project.id, "Review package")
    mentioned = collaboration.post_comment(
        task_id=task.id,
        body="Please review this package @admin",
    )
    collaboration.post_comment(task_id=task.id, body="Latest general update")
    collaboration.touch_task_presence(task.id, activity="editing")

    inbox = collaboration.query_inbox_page(page=1, page_size=20)
    activity = collaboration.list_recent_activity(limit=20)
    presence = collaboration.list_active_presence()

    assert isinstance(
        collaboration._workspace_reader,
        SqlAlchemyCollaborationWorkspaceReader,
    )
    assert [item.comment_id for item in inbox.items] == [mentioned.id]
    assert [item.body_preview for item in activity] == [
        "Latest general update",
        "Please review this package @admin",
    ]
    assert inbox.items[0].unread is True
    assert len(presence) == 1
    assert presence[0].task_name == "Review package"
    assert presence[0].project_name == "Collaboration projection"
    assert presence[0].is_self is True

    collaboration.mark_task_mentions_read(task.id)
    assert collaboration.query_inbox_page(page_size=20).items[0].unread is False


def test_concrete_collaboration_reader_rejects_cross_organization_ids(services) -> None:
    seeded = _seed_priority_pm_rows(services)
    collaboration = services["collaboration_service"]
    now = datetime.now(timezone.utc)
    services["session"].add_all(
        [
            TaskPresenceORM(
                id="phase3d-presence-a",
                task_id=seeded["task_a1"],
                user_id="user-a",
                username="user-a",
                activity="reviewing",
                started_at=now,
                last_seen_at=now,
            ),
            TaskPresenceORM(
                id="phase3d-presence-b",
                task_id=seeded["task_b1"],
                user_id="user-b",
                username="user-b",
                activity="editing",
                started_at=now,
                last_seen_at=now,
            ),
        ]
    )
    services["session"].commit()
    scope = collaboration._tenant_context_service.require_active_scope_ids(
        operation_label="test collaboration reader isolation"
    )
    reader = collaboration._workspace_reader

    comments = reader.read_comment_page(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        accessible_project_ids=(seeded["project_a"], seeded["project_b"]),
        criteria=CollaborationCommentCriteria(),
        page=1,
        page_size=200,
    )
    presence = reader.read_active_presence(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        accessible_project_ids=(seeded["project_a"], seeded["project_b"]),
        active_since=now - timedelta(days=1),
    )

    assert {comment.project_id for comment in comments.items} == {seeded["project_a"]}
    assert seeded["comment_a"] in {comment.comment_id for comment in comments.items}
    assert seeded["comment_b"] not in {comment.comment_id for comment in comments.items}
    assert {row.task_id for row in presence} == {seeded["task_a1"]}


def test_active_presence_returns_complete_current_scoped_set_beyond_legacy_cap(services) -> None:
    project = services["project_service"].create_project("Large active team")
    task = services["task_service"].create_task(project.id, "Presence hub")
    now = datetime.now(timezone.utc)
    services["session"].add_all(
        [
            TaskPresenceORM(
                id=f"complete-presence-{index:03d}",
                task_id=task.id,
                user_id=f"presence-user-{index:03d}",
                username=f"presence-user-{index:03d}",
                activity="reviewing",
                started_at=now,
                last_seen_at=now,
            )
            for index in range(205)
        ]
    )
    services["session"].commit()

    presence = services["collaboration_service"].list_active_presence()

    assert len(presence) == 205
    assert presence[0].username == "presence-user-000"
    assert presence[-1].username == "presence-user-204"


def test_workspace_queries_keep_scoped_project_names(services) -> None:
    auth = services["auth_service"]
    access = services["access_service"]
    projects = services["project_service"]
    tasks = services["task_service"]
    collaboration = services["collaboration_service"]
    alpha = projects.create_project("Visible collaboration")
    beta = projects.create_project("Hidden collaboration")
    alpha_task = tasks.create_task(alpha.id, "Visible task")
    beta_task = tasks.create_task(beta.id, "Hidden task")
    viewer = auth.register_user("phase3d-viewer", "StrongPass123", role_names=["viewer"])
    access.assign_scope_grant(
        scope_type="project",
        scope_id=alpha.id,
        user_id=viewer.id,
        scope_role="viewer",
    )
    collaboration.post_comment(task_id=alpha_task.id, body="Visible @phase3d-viewer")
    collaboration.post_comment(task_id=beta_task.id, body="Hidden update")

    user = auth.authenticate("phase3d-viewer", "StrongPass123")
    services["user_session"].set_principal(auth.build_principal(user))
    inbox = collaboration.query_inbox_page(page_size=20)
    activity = collaboration.list_recent_activity(limit=20)

    assert {item.project_id for item in inbox.items} == {alpha.id}
    assert {item.project_name for item in inbox.items} == {alpha.name}
    assert beta.id not in {item.project_id for item in activity}
