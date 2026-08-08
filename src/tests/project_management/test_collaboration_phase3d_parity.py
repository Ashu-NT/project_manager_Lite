from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskPresenceORM,
)
from src.core.modules.project_management.infrastructure.persistence.reads.collaboration import (
    SqlAlchemyCollaborationWorkspaceReader,
)
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


def test_workspace_reader_preserves_mentions_activity_presence_and_limits(services) -> None:
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

    snapshot = collaboration.list_workspace_snapshot(limit=20)

    assert isinstance(
        collaboration._workspace_reader,
        SqlAlchemyCollaborationWorkspaceReader,
    )
    assert [item.comment_id for item in snapshot.inbox] == [mentioned.id]
    assert [item.body_preview for item in snapshot.recent_activity] == [
        "Latest general update",
        "Please review this package @admin",
    ]
    assert snapshot.inbox[0].unread is True
    assert snapshot.notifications[0].entity_id == mentioned.id
    assert snapshot.notifications[0].attention is True
    assert len(snapshot.active_presence) == 1
    assert snapshot.active_presence[0].task_name == "Review package"
    assert snapshot.active_presence[0].project_name == "Collaboration projection"
    assert snapshot.active_presence[0].is_self is True

    # The legacy contract limits recent comments before filtering mentions.
    assert collaboration.list_inbox(limit=1) == []
    collaboration.mark_task_mentions_read(task.id)
    assert collaboration.list_inbox(limit=20)[0].unread is False


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

    facts = collaboration._workspace_reader.read_facts(
        tenant_id=scope.tenant_id,
        organization_id=scope.organization_id,
        accessible_project_ids=(seeded["project_a"], seeded["project_b"]),
        comment_limit=200,
        presence_since=datetime.now(timezone.utc) - timedelta(days=1),
        presence_limit=200,
    )

    assert {comment.project_id for comment in facts.comments} == {seeded["project_a"]}
    assert seeded["comment_a"] in {comment.comment_id for comment in facts.comments}
    assert seeded["comment_b"] not in {comment.comment_id for comment in facts.comments}
    assert {row.task_id for row in facts.active_presence} == {seeded["task_a1"]}


def test_workspace_reader_keeps_scoped_notification_project_names(services) -> None:
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
    snapshot = collaboration.list_workspace_snapshot(limit=20)

    assert {item.project_id for item in snapshot.inbox} == {alpha.id}
    assert {item.project_name for item in snapshot.inbox} == {alpha.name}
    assert beta.id not in {item.project_id for item in snapshot.recent_activity}
