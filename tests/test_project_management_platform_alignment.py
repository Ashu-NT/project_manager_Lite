from __future__ import annotations

from datetime import date
from pathlib import Path


def test_pm_collaboration_attachments_register_shared_documents(services, repo_workspace, monkeypatch):
    monkeypatch.setattr(
        "infra.modules.project_management.collaboration_attachments.user_data_dir",
        lambda: repo_workspace,
    )
    project = services["project_service"].create_project("PM Document Alignment")
    task = services["task_service"].create_task(
        project.id,
        "Shared Document Comment",
        start_date=date(2026, 3, 19),
        duration_days=1,
    )
    source_dir = repo_workspace / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_file = source_dir / "evidence.txt"
    source_file.write_text("proof", encoding="utf-8")

    comment = services["collaboration_service"].post_comment(
        task_id=task.id,
        body="Please review the attached evidence.",
        attachments=[str(source_file), "ticket-123"],
    )

    stored_file = Path(comment.attachments[0])
    assert stored_file.exists()
    assert stored_file != source_file
    assert comment.attachments[1] == "ticket-123"

    links = services["document_service"].list_links_for_entity(
        module_code="project_management",
        entity_type="task_comment",
        entity_id=comment.id,
    )

    assert len(links) == 2
    assert {link.link_role for link in links} == {"attachment"}

    documents = {document.id: document for document in services["document_service"].list_documents()}
    linked_documents = [documents[link.document_id] for link in links]
    by_uri = {document.storage_uri: document for document in linked_documents}

    assert by_uri[str(stored_file)].storage_kind.value == "FILE_PATH"
    assert by_uri[str(stored_file)].file_name == "evidence.txt"
    assert by_uri["ticket-123"].storage_kind.value == "REFERENCE"
    assert by_uri["ticket-123"].title == "ticket-123"
