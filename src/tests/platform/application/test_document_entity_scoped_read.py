"""DocumentService.list_documents_page_for_entity() -- the real, paginated,
Document-joined, entity-scoped read list_links_for_entity() never provided
(bare, unpaginated DocumentLink rows with no Document metadata). This is
the generic capability the Employee Documents vertical slice (and any
future approved entity) builds on."""

from __future__ import annotations

from src.core.platform.common.exceptions import ValidationError


def test_list_documents_page_for_entity_returns_joined_document_metadata(services) -> None:
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code="EDR-001",
        title="Employment Contract",
        document_type="POLICY",
        storage_kind="FILE_PATH",
        storage_uri="C:/docs/contract.pdf",
    )
    link = document_service.add_link(
        document_id=document.id,
        module_code="platform",
        entity_type="employee",
        entity_id="emp-123",
    )

    page = document_service.list_documents_page_for_entity(
        module_code="platform", entity_type="employee", entity_id="emp-123",
    )

    assert page.total == 1
    assert page.filtered_total == 1
    assert len(page.items) == 1
    row = page.items[0]
    assert row.document.id == document.id
    assert row.document.title == "Employment Contract"
    assert row.link.id == link.id


def test_list_documents_page_for_entity_scoped_to_exact_entity(services) -> None:
    document_service = services["document_service"]
    doc_a = document_service.create_document(
        document_code="EDR-002", title="Doc A", document_type="GENERAL",
        storage_kind="FILE_PATH", storage_uri="C:/docs/a.pdf",
    )
    doc_b = document_service.create_document(
        document_code="EDR-003", title="Doc B", document_type="GENERAL",
        storage_kind="FILE_PATH", storage_uri="C:/docs/b.pdf",
    )
    document_service.add_link(document_id=doc_a.id, module_code="platform", entity_type="employee", entity_id="emp-a")
    document_service.add_link(document_id=doc_b.id, module_code="platform", entity_type="employee", entity_id="emp-b")

    page_a = document_service.list_documents_page_for_entity(
        module_code="platform", entity_type="employee", entity_id="emp-a",
    )
    assert [row.document.id for row in page_a.items] == [doc_a.id]


def test_list_documents_page_for_entity_supports_search_and_pagination(services) -> None:
    document_service = services["document_service"]
    for i in range(30):
        document = document_service.create_document(
            document_code=f"EDR-SEARCH-{i}", title=f"Searchable Doc {i}", document_type="GENERAL",
            storage_kind="FILE_PATH", storage_uri=f"C:/docs/s{i}.pdf",
        )
        document_service.add_link(document_id=document.id, module_code="platform", entity_type="employee", entity_id="emp-search")
    other = document_service.create_document(
        document_code="EDR-OTHER", title="Unrelated Title", document_type="GENERAL",
        storage_kind="FILE_PATH", storage_uri="C:/docs/other.pdf",
    )
    document_service.add_link(document_id=other.id, module_code="platform", entity_type="employee", entity_id="emp-search")

    page_one = document_service.list_documents_page_for_entity(
        module_code="platform", entity_type="employee", entity_id="emp-search",
        page=1, page_size=25, search="Searchable",
    )
    assert page_one.total == 31
    assert page_one.filtered_total == 30
    assert len(page_one.items) == 25

    page_two = document_service.list_documents_page_for_entity(
        module_code="platform", entity_type="employee", entity_id="emp-search",
        page=2, page_size=25, search="Searchable",
    )
    assert len(page_two.items) == 5


def test_list_documents_page_for_entity_active_only_filter(services) -> None:
    document_service = services["document_service"]
    active_doc = document_service.create_document(
        document_code="EDR-ACTIVE", title="Active Doc", document_type="GENERAL",
        storage_kind="FILE_PATH", storage_uri="C:/docs/active.pdf",
    )
    inactive_doc = document_service.create_document(
        document_code="EDR-INACTIVE", title="Inactive Doc", document_type="GENERAL",
        storage_kind="FILE_PATH", storage_uri="C:/docs/inactive.pdf",
    )
    document_service.update_document(inactive_doc.id, is_active=False, expected_version=inactive_doc.version)
    document_service.add_link(document_id=active_doc.id, module_code="platform", entity_type="employee", entity_id="emp-status")
    document_service.add_link(document_id=inactive_doc.id, module_code="platform", entity_type="employee", entity_id="emp-status")

    active_page = document_service.list_documents_page_for_entity(
        module_code="platform", entity_type="employee", entity_id="emp-status", active_only=True,
    )
    assert [row.document.id for row in active_page.items] == [active_doc.id]


def test_list_documents_page_for_entity_type_filter(services) -> None:
    document_service = services["document_service"]
    manual = document_service.create_document(
        document_code="EDR-TYPE-1", title="Manual Doc", document_type="MANUAL",
        storage_kind="FILE_PATH", storage_uri="C:/docs/manual.pdf",
    )
    policy = document_service.create_document(
        document_code="EDR-TYPE-2", title="Policy Doc", document_type="POLICY",
        storage_kind="FILE_PATH", storage_uri="C:/docs/policy.pdf",
    )
    document_service.add_link(document_id=manual.id, module_code="platform", entity_type="employee", entity_id="emp-type")
    document_service.add_link(document_id=policy.id, module_code="platform", entity_type="employee", entity_id="emp-type")

    page = document_service.list_documents_page_for_entity(
        module_code="platform", entity_type="employee", entity_id="emp-type", document_type="MANUAL",
    )
    assert [row.document.id for row in page.items] == [manual.id]


def test_get_document_returns_document_in_active_organization(services) -> None:
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code="EDR-GET", title="Fetchable Doc", document_type="GENERAL",
        storage_kind="FILE_PATH", storage_uri="C:/docs/fetch.pdf",
    )
    fetched = document_service.get_document(document.id)
    assert fetched.id == document.id
    assert fetched.title == "Fetchable Doc"
