from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event

from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskCommentORM,
)
from src.core.platform.common.exceptions import NotFoundError
from src.tests.project_management._test_repository_tenant_hardening_helpers import (
    _seed_priority_pm_rows,
)


def test_task_detail_comment_pages_remain_bounded_and_stably_ordered(services) -> None:
    project = services["project_service"].create_project("R7E discussion paging")
    task = services["task_service"].create_task(project.id, "Discuss")
    session = services["session"]
    now = datetime.now(timezone.utc)
    session.add_all(
        TaskCommentORM(
            id=f"r7e-page-{index:04d}",
            task_id=task.id,
            author_username="author",
            body=f"Comment {index}",
            created_at=now + timedelta(seconds=index // 2),
        )
        for index in range(1000)
    )
    session.commit()

    service = services["collaboration_service"]
    statements: list[str] = []

    def record_statement(_connection, _cursor, statement, _parameters, _context, _many):
        if "task_comments" in statement.lower():
            statements.append(statement.lower())

    event.listen(session.bind, "before_cursor_execute", record_statement)
    try:
        first = service.query_task_comments_page(task.id, page=1, page_size=25)
        first_query_count = len(statements)
        statements.clear()
        last = service.query_task_comments_page(task.id, page=40, page_size=25)
        last_query_count = len(statements)
    finally:
        event.remove(session.bind, "before_cursor_execute", record_statement)

    assert first.total == last.total == 1000
    assert len(first.items) == len(last.items) == 25
    assert first_query_count == last_query_count == 2
    assert first.items[0].id == "r7e-page-0998"
    assert first.items[1].id == "r7e-page-0999"
    assert last.items[-1].id == "r7e-page-0001"
    assert {item.id for item in first.items}.isdisjoint(item.id for item in last.items)


def test_task_detail_comment_page_rejects_foreign_task(services) -> None:
    seeded = _seed_priority_pm_rows(services)
    service = services["collaboration_service"]

    assert service.query_task_comments_page(seeded["task_a1"]).total >= 1
    with pytest.raises(NotFoundError):
        service.query_task_comments_page(seeded["task_b1"])
