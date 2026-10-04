import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import event, select

from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskCommentORM,
)


def test_mark_mentions_read_queries_only_recipient_rows_in_bounded_batches(services) -> None:
    project = services["project_service"].create_project("Mention read batch")
    task = services["task_service"].create_task(project.id, "Review")
    principal = services["user_session"].principal
    now = datetime.now(timezone.utc)
    session = services["session"]
    rows = []
    for index in range(1100):
        is_mention = index < 101
        rows.append(
            TaskCommentORM(
                id=f"r7e-read-{index:04d}",
                task_id=task.id,
                author_username="author",
                body=f"Comment {index}",
                mentions_json='["admin"]' if is_mention else "[]",
                mentioned_user_ids_json=(
                    json.dumps([principal.user_id]) if is_mention else "[]"
                ),
                created_at=now + timedelta(seconds=index),
            )
        )
    session.add_all(rows)
    session.commit()

    reads: list[str] = []

    def record(_connection, _cursor, sql, _params, _context, _many):
        normalized = sql.lower()
        if "from task_comments" in normalized and "limit" in normalized:
            reads.append(normalized)

    event.listen(session.bind, "before_cursor_execute", record)
    try:
        services["collaboration_service"].mark_task_mentions_read(task.id)
    finally:
        event.remove(session.bind, "before_cursor_execute", record)

    assert len(reads) == 3
    assert all("limit" in sql for sql in reads)
    persisted = session.scalars(
        select(TaskCommentORM).where(TaskCommentORM.task_id == task.id)
    ).all()
    assert sum(principal.user_id in json.loads(row.read_by_user_ids_json) for row in persisted) == 101
