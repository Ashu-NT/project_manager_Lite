"""`DocumentService.list_documents_page_for_organization` -- a tenant-scoped
(not active-organization-scoped) paginated read, added for Organization
Detail's Documents tab so an admin can view ANY organization's documents
regardless of which organization is currently active in their own session.

Read-only: create/update continue using the caller's active organization
unchanged (see test_document_platform_foundation.py). Does not touch
DocumentLink at all -- link/unlink semantics are untouched by this slice."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.core.platform.common.exceptions import NotFoundError
from src.core.platform.infrastructure.persistence.orm.master_data.documents.documents import (
    DocumentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import (
    OrganizationORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import (
    TenantORM,
)


def test_viewing_a_non_active_organization_returns_its_own_documents_correctly(services) -> None:
    organization_service = services["organization_service"]
    document_service = services["document_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="ORG-A", display_name="Org A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    document_service.create_document(document_code="A-DOC-1", title="A Document One", storage_uri="C:/docs/a1.pdf")
    document_service.create_document(document_code="A-DOC-2", title="A Document Two", storage_uri="C:/docs/a2.pdf")

    org_b = organization_service.create_organization(
        organization_code="ORG-B", display_name="Org B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    document_service.create_document(document_code="B-DOC-1", title="B Document One", storage_uri="C:/docs/b1.pdf")

    # Session-active org is now B; ask for A's documents anyway.
    page = document_service.list_documents_page_for_organization(org_a.id, page=1, page_size=25)

    titles = sorted(document.title for document in page.items)
    assert titles == ["A Document One", "A Document Two"]
    assert page.total == 2
    assert page.filtered_total == 2
    for document in page.items:
        assert document.organization_id == org_a.id


def test_no_leakage_from_the_active_organization_into_the_viewed_organization(services) -> None:
    organization_service = services["organization_service"]
    document_service = services["document_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="LEAK-A", display_name="Leak A", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_a.id)
    document_service.create_document(document_code="LEAK-A-1", title="Leak A Document", storage_uri="C:/docs/la.pdf")

    org_b = organization_service.create_organization(
        organization_code="LEAK-B", display_name="Leak B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)
    document_service.create_document(document_code="LEAK-B-1", title="Leak B Document", storage_uri="C:/docs/lb.pdf")

    # Still active in B; explicitly ask for B's own documents -- must not
    # also include anything from A, proving the query is genuinely
    # org-filtered and not accidentally returning the whole tenant.
    page = document_service.list_documents_page_for_organization(org_b.id, page=1, page_size=25)
    titles = {document.title for document in page.items}
    assert titles == {"Leak B Document"}
    assert "Leak A Document" not in titles


def test_cross_tenant_organization_id_is_rejected_not_visible(services) -> None:
    session = services["session"]
    document_service = services["document_service"]
    tenant_context_service = services["tenant_context_service"]
    caller_tenant_id = tenant_context_service.require_active_tenant_id(operation_label="test setup")

    foreign_tenant_id = "foreign-tenant-doc-xyz"
    foreign_org_id = "foreign-org-doc-xyz"
    now = datetime.now(timezone.utc)
    session.add(
        TenantORM(
            id=foreign_tenant_id,
            tenant_code="FOREIGN-TENANT-DOC",
            display_name="Foreign Tenant",
            version=1,
        )
    )
    session.commit()
    session.add(
        OrganizationORM(
            id=foreign_org_id,
            tenant_id=foreign_tenant_id,
            organization_code="FOREIGN-DOC",
            display_name="Foreign Org",
            timezone_name="UTC",
            base_currency="USD",
            status="active",
            version=1,
        )
    )
    session.commit()
    session.add(
        DocumentORM(
            id="foreign-document-1",
            tenant_id=foreign_tenant_id,
            organization_id=foreign_org_id,
            document_code="FOREIGN-DOC-1",
            title="Foreign Document",
            document_type="GENERAL",
            storage_kind="FILE_PATH",
            storage_uri="C:/docs/foreign.pdf",
            uploaded_at=now,
            is_current=True,
            is_active=True,
            version=1,
        )
    )
    session.commit()

    assert foreign_tenant_id != caller_tenant_id
    with pytest.raises(NotFoundError):
        document_service.list_documents_page_for_organization(foreign_org_id, page=1, page_size=25)


def test_inactive_and_archived_organizations_still_have_readable_document_history(services) -> None:
    organization_service = services["organization_service"]
    document_service = services["document_service"]
    tenant_context_service = services["tenant_context_service"]

    org = organization_service.create_organization(
        organization_code="HIST-DOC", display_name="History Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org.id)
    document_service.create_document(document_code="HIST-DOC-1", title="History Document", storage_uri="C:/docs/hist.pdf")

    other = organization_service.create_organization(
        organization_code="HIST-DOC-OTHER", display_name="History Other", timezone_name="UTC", base_currency="USD"
    )
    organization_service.deactivate_organization(org.id)
    tenant_context_service.set_active_organization(other.id)

    page = document_service.list_documents_page_for_organization(org.id, page=1, page_size=25)
    assert [document.title for document in page.items] == ["History Document"]

    organization_service.archive_organization(org.id)
    page = document_service.list_documents_page_for_organization(org.id, page=1, page_size=25)
    assert [document.title for document in page.items] == ["History Document"]


def test_mutation_paths_still_use_the_active_organization_not_the_viewed_one(services) -> None:
    """create_document()/update_document() are unaffected by this read-only
    addition -- they keep using the caller's active organization, the
    existing, unchanged domain rule (do not weaken mutation scoping)."""
    organization_service = services["organization_service"]
    document_service = services["document_service"]
    tenant_context_service = services["tenant_context_service"]

    org_a = organization_service.create_organization(
        organization_code="MUT-DOC-A", display_name="Mutation A", timezone_name="UTC", base_currency="USD"
    )
    org_b = organization_service.create_organization(
        organization_code="MUT-DOC-B", display_name="Mutation B", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(org_b.id)

    created = document_service.create_document(
        document_code="MUT-DOC", title="Mutation Document", storage_uri="C:/docs/mut.pdf"
    )
    assert created.organization_id == org_b.id

    page_a = document_service.list_documents_page_for_organization(org_a.id, page=1, page_size=25)
    assert page_a.items == []
    page_b = document_service.list_documents_page_for_organization(org_b.id, page=1, page_size=25)
    assert [d.title for d in page_b.items] == ["Mutation Document"]
