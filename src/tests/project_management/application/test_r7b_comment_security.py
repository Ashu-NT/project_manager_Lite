import pytest
from sqlalchemy import text

from src.core.modules.project_management.api.desktop.collaboration.serializers.collaboration_serializers import (
    serialize_inbox_item,
)
from src.core.platform.common.exceptions import DomainError
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


@pytest.mark.parametrize("operation", ["create", "read", "edit", "delete"])
def test_service_rejects_foreign_scope_without_database_rls(services, operation):
    seeded = _seed_priority_pm_rows(services)
    with pytest.raises(DomainError):
        if operation == "create":
            services["collaboration_comment_commands"].post_comment(task_id=seeded["task_b1"], body="attack")
        elif operation == "read":
            services["collaboration_comment_query"].query_task_comments_page(seeded["task_b1"])
        elif operation == "edit":
            services["collaboration_comment_commands"].edit_comment(seeded["comment_b"], "attack")
        else:
            services["collaboration_comment_commands"].delete_comment(seeded["comment_b"])


def test_same_organization_foreign_project_rejected_by_service(services):
    visible = services['project_create'].create_project("Visible")
    hidden = services['project_create'].create_project("Hidden")
    task = services['task_lifecycle_commands'].create_task(hidden.id, "Private task")
    comment = services["collaboration_comment_commands"].post_comment(task_id=task.id, body="Private project comment")
    user = services["user_registration"].register_user("r7b-reader", "StrongPass123", role_names=["viewer"])
    services["access_service"].assign_scope_grant(
        scope_type="project", scope_id=visible.id, user_id=user.id, scope_role="viewer"
    )
    services["user_session"].set_principal(
        services["principal_builder"].build(services["authentication"].authenticate("r7b-reader", "StrongPass123"))
    )
    for operation in (
        lambda: services["collaboration_comment_query"].query_task_comments_page(task.id),
        lambda: services["collaboration_comment_commands"].post_comment(task_id=task.id, body="attack"),
        lambda: services["collaboration_comment_commands"].edit_comment(comment.id, "attack"),
        lambda: services["collaboration_comment_commands"].delete_comment(comment.id),
    ):
        with pytest.raises(DomainError):
            operation()
    assert services["collaboration_inbox_query"].list_recent_activity(project_id=hidden.id) == []


def test_deleted_comment_is_redacted_in_activity_dto_audit_and_read_marks(
    services, monkeypatch
):
    from src.core.modules.project_management.application.collaboration.commands import (
        collaboration_comments,
    )

    activity_intents = []
    record = collaboration_comments.record_activity

    def capture_activity(*args, **kwargs):
        activity_intents.append(kwargs)
        return record(*args, **kwargs)

    monkeypatch.setattr(collaboration_comments, "record_activity", capture_activity)
    project = services['project_create'].create_project("Privacy")
    task = services['task_lifecycle_commands'].create_task(project.id, "Task")
    secret = "PRIVATE-CONTENT @admin"
    comment = services["collaboration_comment_commands"].post_comment(task_id=task.id, body=secret)
    services["collaboration_comment_commands"].delete_comment(comment.id, expected_revision=comment.version)
    services["collaboration_comment_engagement"].mark_task_mentions_read(task.id)
    assert services["collaboration_inbox_query"].query_mentions_page(project_id=project.id).total == 0
    item = next(
        item
        for item in services["collaboration_inbox_query"].list_recent_activity(project_id=project.id)
        if item.comment_id == comment.id
    )
    assert item.is_deleted and not item.body_preview
    assert serialize_inbox_item(item).body_preview == "This comment was deleted."
    for table in ("activity_entries", "audit_entries"):
        rows = (
            services["session"]
            .execute(
                text(f"SELECT * FROM {table} WHERE entity_id=:id"), {"id": comment.id}
            )
            .all()
        )
        if table == "audit_entries":
            assert rows
        assert secret not in str(rows)
    assert activity_intents and secret not in str(activity_intents)
    other = services['project_create'].create_project("Different project")
    assert services["collaboration_inbox_query"].list_recent_activity(project_id=other.id) == []
