"""P44B-FIX: TaskComment attachment/linked-document cross-capability atomicity.

Proves the corrected transaction boundary -- `post_comment`'s attachment and
linked-document integration with the Document capability now shares ONE
physical transaction with the TaskComment write, via
`register_entity_attachments_in_uow`/`link_existing_document_in_uow`
(transaction-neutral, never commit/rollback/publish) invoked directly inside
`CollaborationUnitOfWork` (extended with `documents`/`links`/`structures`
accessors mirroring `ProjectUnitOfWork.financial_profiles`'s precedent).

All assertions check actual DB row state, never commit counts.
"""

from __future__ import annotations

from sqlalchemy import func, select

from src.core.modules.project_management.application.collaboration.event_handlers.view_invalidation import (
    COLLABORATION_WORKSPACE_SCOPE_CODE,
    TASK_COMMENT_CATEGORY,
    TASK_COMMENT_SCOPE_CODE,
)
from src.core.modules.project_management.infrastructure.persistence.orm.collaboration import (
    TaskCommentORM,
)
from src.core.modules.project_management.infrastructure.persistence.repositories.collaboration.collaboration import (
    SqlAlchemyTaskCommentRepository,
)
from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
    DOCUMENT_CATEGORY,
)
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import (
    DocumentLinkORM,
    DocumentORM,
)
from src.core.platform.infrastructure.persistence.repositories.master_data.documents.documents import (
    SqlAlchemyDocumentRepository,
)

import pytest


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _spy_hints(services):
    hints: list = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(
        _AnyOrgFilter(), lambda hint: hints.append(hint)
    )
    return hints


def _comment_hints(hints):
    return [h for h in hints if h.category == TASK_COMMENT_CATEGORY]


def _document_hints(hints):
    return [h for h in hints if h.category == DOCUMENT_CATEGORY]


def _count(services, model) -> int:
    return services["session"].execute(select(func.count()).select_from(model)).scalar_one()


def _setup(services):
    project = services["project_service"].create_project("P44B-FIX attachment project")
    task = services["task_service"].create_task(project.id, "P44B-FIX attachment task")
    return project, task


def _make_existing_document(services) -> str:
    documents = services["collaboration_service"]._document_integration_service.register_entity_attachments(
        required_permission="collaboration.manage",
        operation_label="seed existing document for link test",
        module_code="project_management",
        entity_type="task_comment_fixture_seed",
        entity_id="seed-entity",
        attachments=["seed-reference.txt"],
        source_system="project_management",
    )
    return documents[0].id


# ---------------------------------------------------------------------------
# Success path (§21): one physical transaction, both capabilities' facts
# ---------------------------------------------------------------------------


def test_post_comment_with_attachment_and_link_is_one_atomic_transaction(services):
    _, task = _setup(services)
    existing_document_id = _make_existing_document(services)
    hints = _spy_hints(services)

    before_documents = _count(services, DocumentORM)
    before_links = _count(services, DocumentLinkORM)

    comment = services["collaboration_service"].post_comment(
        task_id=task.id,
        body="See attached and the linked reference",
        attachments=["notes.txt"],
        linked_document_ids=[existing_document_id],
    )

    assert _count(services, DocumentORM) == before_documents + 1, "one new Document for the attachment"
    assert _count(services, DocumentLinkORM) == before_links + 2, (
        "one link for the new attachment, one link for the existing linked document"
    )

    comment_row = services["session"].execute(
        select(TaskCommentORM).where(TaskCommentORM.id == comment.id)
    ).scalar_one()
    assert comment_row is not None

    audit_rows = services["session"].execute(
        select(AuditEntryORM).where(AuditEntryORM.entity_id == comment.id)
    ).scalars().all()
    assert [row.operation for row in audit_rows] == ["create"], "comment's own audit"

    document_audit_rows = services["session"].execute(
        select(AuditEntryORM).where(AuditEntryORM.entity_type == "document")
    ).scalars().all()
    assert len(document_audit_rows) >= 2, (
        "one audit row for the newly-created attachment document, one for the linked-existing-document update"
    )

    assert {h.scope_code for h in _comment_hints(hints)} == {
        TASK_COMMENT_SCOPE_CODE,
        COLLABORATION_WORKSPACE_SCOPE_CODE,
    }
    assert len(_document_hints(hints)) > 0, "Document capability's own typed events also fire postcommit"


def test_post_comment_without_attachment_never_touches_document_capability(services):
    _, task = _setup(services)
    hints = _spy_hints(services)
    before_documents = _count(services, DocumentORM)
    before_links = _count(services, DocumentLinkORM)

    services["collaboration_service"].post_comment(task_id=task.id, body="Plain text only")

    assert _count(services, DocumentORM) == before_documents
    assert _count(services, DocumentLinkORM) == before_links
    assert _document_hints(hints) == []


# ---------------------------------------------------------------------------
# Attachment/Document failure AFTER comment staged in the SAME transaction (§17)
# ---------------------------------------------------------------------------


def test_document_registration_failure_rolls_back_the_already_staged_comment(services, monkeypatch):
    _, task = _setup(services)
    hints = _spy_hints(services)

    before_comments = _count(services, TaskCommentORM)
    before_documents = _count(services, DocumentORM)
    before_links = _count(services, DocumentLinkORM)
    before_audit = _count(services, AuditEntryORM)

    def _boom(self, document) -> None:
        raise RuntimeError("simulated document registration failure")

    monkeypatch.setattr(SqlAlchemyDocumentRepository, "add", _boom)

    with pytest.raises(RuntimeError):
        services["collaboration_service"].post_comment(
            task_id=task.id, body="Should never persist", attachments=["will-fail.txt"]
        )

    monkeypatch.undo()

    assert _count(services, TaskCommentORM) == before_comments, (
        "the comment was already staged in this same transaction -- it must roll back too"
    )
    assert _count(services, DocumentORM) == before_documents
    assert _count(services, DocumentLinkORM) == before_links
    assert _count(services, AuditEntryORM) == before_audit
    assert hints == [], "no postcommit hints for either capability"


# ---------------------------------------------------------------------------
# TaskComment persistence failure (§18): Document work never even runs
# ---------------------------------------------------------------------------


def test_comment_persistence_failure_prevents_any_document_state(services, monkeypatch):
    _, task = _setup(services)
    hints = _spy_hints(services)

    before_comments = _count(services, TaskCommentORM)
    before_documents = _count(services, DocumentORM)
    before_audit = _count(services, AuditEntryORM)

    def _boom(self, comment) -> None:
        raise RuntimeError("simulated comment persistence failure")

    monkeypatch.setattr(SqlAlchemyTaskCommentRepository, "add", _boom)

    with pytest.raises(RuntimeError):
        services["collaboration_service"].post_comment(
            task_id=task.id, body="Should never persist either", attachments=["also-fails.txt"]
        )

    monkeypatch.undo()

    assert _count(services, TaskCommentORM) == before_comments
    assert _count(services, DocumentORM) == before_documents
    assert _count(services, AuditEntryORM) == before_audit
    assert hints == []


# ---------------------------------------------------------------------------
# Transactional handler failure (§19): FAIL_FAST, no partial cross-capability state
# ---------------------------------------------------------------------------


def test_transactional_handler_failure_rolls_back_both_capabilities(services):
    _, task = _setup(services)
    existing_document_id = _make_existing_document(services)
    hints = _spy_hints(services)

    before_comments = _count(services, TaskCommentORM)
    before_documents = _count(services, DocumentORM)
    before_links = _count(services, DocumentLinkORM)

    from src.core.modules.project_management.application.collaboration.collaboration_events import (
        TaskCommentChanged,
    )

    dispatcher = services["collaboration_service"]._uow_factory._transactional_dispatcher

    def _raising_handler(event, uow) -> None:
        raise RuntimeError("simulated transactional handler failure")

    dispatcher.subscribe(TaskCommentChanged, _raising_handler)

    with pytest.raises(RuntimeError):
        services["collaboration_service"].post_comment(
            task_id=task.id,
            body="Handler will explode",
            attachments=["never-lands.txt"],
            linked_document_ids=[existing_document_id],
        )

    assert _count(services, TaskCommentORM) == before_comments
    assert _count(services, DocumentORM) == before_documents
    assert _count(services, DocumentLinkORM) == before_links
    assert hints == []


# ---------------------------------------------------------------------------
# Physical commit failure (§20)
# ---------------------------------------------------------------------------


def test_physical_commit_failure_persists_neither_capability(services, monkeypatch):
    from sqlalchemy.orm import Session

    _, task = _setup(services)
    hints = _spy_hints(services)

    before_comments = _count(services, TaskCommentORM)
    before_documents = _count(services, DocumentORM)

    real_commit = Session.commit

    def _boom(self):
        raise RuntimeError("simulated physical commit failure")

    monkeypatch.setattr(Session, "commit", _boom)

    with pytest.raises(RuntimeError):
        services["collaboration_service"].post_comment(
            task_id=task.id, body="Commit itself will fail", attachments=["irrelevant.txt"]
        )

    monkeypatch.setattr(Session, "commit", real_commit)

    assert _count(services, TaskCommentORM) == before_comments
    assert _count(services, DocumentORM) == before_documents
    assert hints == []


# ---------------------------------------------------------------------------
# Retry/idempotency characterization (§22): a failed attempt leaves nothing
# durable, so retrying the identical logical operation produces exactly one
# final result, never a duplicate.
# ---------------------------------------------------------------------------


def test_retry_after_failed_attempt_produces_exactly_one_comment_and_one_document(services, monkeypatch):
    _, task = _setup(services)

    def _boom(self, document) -> None:
        raise RuntimeError("simulated failure on first attempt")

    monkeypatch.setattr(SqlAlchemyDocumentRepository, "add", _boom)
    with pytest.raises(RuntimeError):
        services["collaboration_service"].post_comment(
            task_id=task.id, body="Retry me", attachments=["retry.txt"]
        )
    monkeypatch.undo()

    before_comments = _count(services, TaskCommentORM)
    before_documents = _count(services, DocumentORM)

    services["collaboration_service"].post_comment(
        task_id=task.id, body="Retry me", attachments=["retry.txt"]
    )

    assert _count(services, TaskCommentORM) == before_comments + 1
    assert _count(services, DocumentORM) == before_documents + 1
