from sqlalchemy import event

from src.core.platform.access.application.dto.commands.scoped_access import (
    ScopedAccessGrantAssignCommand,
    ScopedAccessGrantRemoveCommand,
)
from src.core.platform.common.exceptions import ValidationError


def test_mention_search_uses_effective_scope_and_revocation(services) -> None:
    access = services["access_service"]
    project = services['project_create'].create_project("Mention search")
    task = services['task_lifecycle_commands'].create_task(project.id, "Discussion")
    user = services["user_registration"].register_user(
        "r7e-mention-search", "StrongPass123", role_names=[],
        tenant_id=services["tenant_context_service"].get_active_tenant_id(),
    )

    assert all(item.user_id != user.id for item in services["collaboration_comment_query"].list_mention_candidates(task.id))
    access.assign_scope_grant(
        ScopedAccessGrantAssignCommand(scope_type="project", scope_id=project.id, user_id=user.id, scope_role="viewer"))

    statements: list[str] = []
    session = services["session"]

    def record(_connection, _cursor, sql, _params, _context, _many):
        if "users" in sql.lower():
            statements.append(sql)

    event.listen(session.bind, "before_cursor_execute", record)
    try:
        candidates = services["collaboration_comment_query"].list_mention_candidates(task.id, query="mention-search")
    finally:
        event.remove(session.bind, "before_cursor_execute", record)

    assert [(item.user_id, item.handle) for item in candidates] == [
        (user.id, "r7e-mention-search")
    ]
    assert len(statements) == 1

    access.remove_scope_grant(ScopedAccessGrantRemoveCommand(scope_type="project", scope_id=project.id, user_id=user.id))
    assert all(item.user_id != user.id for item in services["collaboration_comment_query"].list_mention_candidates(task.id))
    try:
        services["collaboration_comment_commands"].post_comment(task_id=task.id, body="@r7e-mention-search please review")
    except ValidationError as exc:
        assert exc.code == "COLLABORATION_MENTION_UNKNOWN"
    else:
        raise AssertionError("Revoked mention recipient was accepted")
