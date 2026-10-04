from datetime import datetime, timezone

from sqlalchemy import event

from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import (
    DocumentORM,
)


def test_task_document_selector_is_bounded_and_scoped(services) -> None:
    project = services["project_service"].create_project("Document selector")
    task = services["task_service"].create_task(project.id, "Evidence")
    scope = services["tenant_context_service"].require_active_scope_ids(
        operation_label="seed document selector"
    )
    session = services["session"]
    now = datetime.now(timezone.utc)
    session.add_all(
        DocumentORM(
            id=f"r7e-doc-{index:04d}",
            tenant_id=scope.tenant_id,
            organization_id=scope.organization_id,
            document_code=f"R7E-DOC-{index:04d}",
            title=f"Evidence {index:04d}",
            document_type="GENERAL",
            storage_kind="REFERENCE",
            storage_uri=f"ref-{index:04d}",
            uploaded_at=now,
        )
        for index in range(150)
    )
    session.commit()
    service = services["collaboration_service"]
    statements: list[str] = []

    def record(_connection, _cursor, sql, _params, _context, _many):
        if "documents" in sql.lower():
            statements.append(sql)

    event.listen(session.bind, "before_cursor_execute", record)
    try:
        first = service.search_available_documents(task.id)
        found = service.search_available_documents(task.id, query="0149")
    finally:
        event.remove(session.bind, "before_cursor_execute", record)

    assert len(first) == 50
    assert first[0].document_code == "R7E-DOC-0000"
    assert [(item.id, item.title) for item in found] == [
        ("r7e-doc-0149", "Evidence 0149")
    ]
    assert len(statements) == 2
