from __future__ import annotations

from datetime import date
from pathlib import Path

from core.platform.common.models import WorkerType
from core.platform.notifications.domain_events import DomainChangeEvent, domain_events
from ui.modules.project_management.collaboration.tab import CollaborationTab
from ui.modules.project_management.resource.dialogs import ResourceEditDialog
from ui.modules.project_management.resource.tab import ResourceTab
from ui.modules.project_management.task.collaboration_dialog import TaskCollaborationDialog


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


def test_pm_task_collaboration_dialog_distinguishes_linked_documents(qapp, services, repo_workspace, monkeypatch):
    monkeypatch.setattr(
        "infra.modules.project_management.collaboration_attachments.user_data_dir",
        lambda: repo_workspace,
    )
    project = services["project_service"].create_project("PM Document UX")
    task = services["task_service"].create_task(
        project.id,
        "Shared Document Visibility",
        start_date=date(2026, 3, 19),
        duration_days=1,
    )
    source_dir = repo_workspace / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_file = source_dir / "procedure.pdf"
    source_file.write_text("procedure", encoding="utf-8")

    services["collaboration_service"].post_comment(
        task_id=task.id,
        body="See the latest procedure and ticket reference.",
        attachments=[str(source_file), "ticket-123"],
    )

    dialog = TaskCollaborationDialog(
        None,
        collaboration_service=services["collaboration_service"],
        task_id=task.id,
        task_name=task.name,
        username="admin",
        mention_aliases=["admin"],
    )

    assert dialog.activity_list.count() == 1
    rendered = dialog.activity_list.item(0).text()
    assert "Linked documents:" in rendered
    assert "procedure.pdf [General | File]" in rendered
    assert "ticket-123 [General | Reference]" in rendered
    assert "Attachment references:" in rendered


def test_pm_resource_ui_surfaces_shared_employee_context(qapp, services):
    employee = services["employee_service"].create_employee(
        employee_code="EMP-CTX-001",
        full_name="Alice Admin",
        department="Operations",
        site_name="Berlin Plant",
        title="Planner",
        email="alice@example.com",
    )
    resource = services["resource_service"].create_resource(
        "",
        hourly_rate=95.0,
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )

    tab = ResourceTab(
        resource_service=services["resource_service"],
        employee_service=services["employee_service"],
        user_session=services["user_session"],
    )

    assert tab.model.data(tab.model.index(0, 7)) == "Operations | Berlin Plant"
    assert tab.model.data(tab.model.index(0, 8)) == "alice@example.com"

    dialog = ResourceEditDialog(
        resource=resource,
        employee_service=services["employee_service"],
    )
    employee_index = dialog.employee_combo.findData(employee.id)
    assert employee_index >= 0
    assert "Operations | Berlin Plant" in dialog.employee_combo.itemText(employee_index)
    assert dialog.employee_context_value.text() == "Operations | Berlin Plant"

    updated = services["employee_service"].update_employee(
        employee.id,
        department="Planning",
        site_name="Lagos Hub",
        expected_version=employee.version,
    )
    qapp.processEvents()

    assert updated.department == "Planning"
    assert tab.model.data(tab.model.index(0, 7)) == "Planning | Lagos Hub"


def test_pm_resource_tab_refreshes_from_generic_domain_event(qapp, services):
    employee = services["employee_service"].create_employee(
        employee_code="EMP-CTX-002",
        full_name="Ben Example",
        department="Planning",
        site_name="Berlin Plant",
        title="Coordinator",
        email="ben@example.com",
    )
    services["resource_service"].create_resource(
        "",
        hourly_rate=100.0,
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )
    tab = ResourceTab(
        resource_service=services["resource_service"],
        employee_service=services["employee_service"],
        user_session=services["user_session"],
    )

    tab.model.set_employee_contexts({employee.id: "STALE"})
    assert tab.model.data(tab.model.index(0, 7)) == "STALE"

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="platform",
            scope_code="platform",
            entity_type="employee",
            entity_id=employee.id,
            source_event="employees_changed",
        )
    )
    qapp.processEvents()

    assert tab.model.data(tab.model.index(0, 7)) == "Planning | Berlin Plant"


def test_pm_resource_tab_refreshes_from_shared_master_bridge(qapp, services):
    employee = services["employee_service"].create_employee(
        employee_code="EMP-CTX-003",
        full_name="Cara Example",
        department="Operations",
        site_name="Lagos Hub",
        title="Planner",
        email="cara@example.com",
    )
    site = services["site_service"].create_site(site_code="LAG", name="Lagos Hub")
    services["resource_service"].create_resource(
        "",
        hourly_rate=105.0,
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
    )
    tab = ResourceTab(
        resource_service=services["resource_service"],
        employee_service=services["employee_service"],
        user_session=services["user_session"],
    )

    tab.model.set_employee_contexts({employee.id: "STALE"})
    assert tab.model.data(tab.model.index(0, 7)) == "STALE"

    domain_events.sites_changed.emit(site.id)
    qapp.processEvents()

    assert tab.model.data(tab.model.index(0, 7)) == "Operations | Lagos Hub"


def test_pm_collaboration_tab_refreshes_from_generic_domain_event(qapp, services):
    project = services["project_service"].create_project("PM Generic Collaboration")
    task = services["task_service"].create_task(
        project.id,
        "Generic Collaboration Task",
        start_date=date(2026, 3, 19),
        duration_days=1,
    )
    services["collaboration_service"].post_comment(task_id=task.id, body="Please review this update")
    tab = CollaborationTab(collaboration_service=services["collaboration_service"])

    assert tab.activity_label.text() == "Recent updates: 1"
    tab.activity_label.setText("Recent updates: 99")

    domain_events.domain_changed.emit(
        DomainChangeEvent(
            category="module",
            scope_code="project_management",
            entity_type="task_collaboration",
            entity_id=task.id,
            source_event="collaboration_changed",
        )
    )
    qapp.processEvents()

    assert tab.activity_label.text() == "Recent updates: 1"
