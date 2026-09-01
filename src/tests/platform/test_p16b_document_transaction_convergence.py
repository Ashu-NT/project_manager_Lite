from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.infrastructure.persistence.uow.document_unit_of_work import (
    SqlAlchemyDocumentUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------
#
# P16C superseded this file's original documents_changed-emission proofs for
# create_document/update_document (typed DocumentCreated/DocumentProfileUpdated replaced them);
# P16D then deleted documents_changed entirely, so every remaining `_spy_signal(domain_events.
# documents_changed)` use in this file (DocumentLink section included) has been dropped too --
# the write-outcome/rollback assertions below are unaffected and remain the real coverage. See
# test_p16c_document_typed_events.py and test_p16d_document_link_typed_events.py for the current
# event-emission proofs.


def test_create_document_still_persists(services):
    document_service = services["document_service"]
    code = _unique_code("DOC-CREATE")
    document = document_service.create_document(
        document_code=code, title="Create Ok", storage_uri="C:/docs/a.pdf"
    )

    assert document.document_code == code
    reloaded = document_service._document_repo.get(document.id)
    assert reloaded is not None
    assert reloaded.document_code == code


def test_update_document_real_change_still_persists(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("DOC-UPDATE"), title="Before", storage_uri="C:/docs/b.pdf"
    )

    updated = document_service.update_document(
        document.id, title="After", expected_version=document.version
    )

    assert updated.title == "After"
    reloaded = document_service._document_repo.get(document.id)
    assert reloaded.title == "After"


def test_update_document_no_op_produces_zero_write_zero_audit(services, monkeypatch):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("DOC-NOOP"), title="Same", storage_uri="C:/docs/c.pdf"
    )
    before = document_service._document_repo.get(document.id)
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = document_service.update_document(
        document.id, title="Same", storage_uri="C:/docs/c.pdf", expected_version=document.version
    )

    assert result.version == document.version
    assert audit_calls == []
    reloaded = document_service._document_repo.get(document.id)
    assert reloaded.version == before.version


def test_create_document_duplicate_code_rolls_back(services):
    document_service = services["document_service"]
    code = _unique_code("DOC-DUPE")
    document_service.create_document(document_code=code, title="First", storage_uri="C:/docs/d.pdf")

    with pytest.raises(ValidationError, match="Document code already exists"):
        document_service.create_document(document_code=code, title="Second", storage_uri="C:/docs/e.pdf")


def test_update_document_cross_org_denied(services):
    document_service = services["document_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    document = document_service.create_document(
        document_code=_unique_code("DOC-CROSSORG"), title="Home Org Doc", storage_uri="C:/docs/f.pdf"
    )

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("DOC-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            document_service.update_document(document.id, title="Hijacked")
    finally:
        tenant_context_service.set_active_organization(default_organization.id)


def test_update_document_stale_version_raises(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("DOC-STALE"), title="Stale Doc", storage_uri="C:/docs/g.pdf"
    )

    with pytest.raises(ConcurrencyError):
        document_service.update_document(
            document.id, title="Should Not Apply", expected_version=document.version + 1
        )


def test_create_document_audit_failure_rolls_back(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated document audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    document_service = services["document_service"]
    code = _unique_code("DOC-AUDITFAIL")

    with pytest.raises(RuntimeError, match="simulated document audit failure"):
        document_service.create_document(document_code=code, title="Audit Fail", storage_uri="C:/docs/h.pdf")

    monkeypatch.undo()
    organization = document_service._tenant_context_service.get_active_organization()
    assert document_service._document_repo.get_by_code(organization.id, code) is None


def test_create_document_commit_failure_rolls_back(services, monkeypatch):
    document_service = services["document_service"]
    code = _unique_code("DOC-COMMITFAIL")

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        document_service.create_document(document_code=code, title="Commit Fail", storage_uri="C:/docs/i.pdf")


# ---------------------------------------------------------------------------
# DocumentStructure
# ---------------------------------------------------------------------------


def test_create_document_structure_still_persists(services):
    document_service = services["document_service"]
    code = _unique_code("STRUCT-CREATE")

    structure = document_service.create_document_structure(structure_code=code, name="Manuals")

    assert structure.structure_code == code.replace("-", "_")


def test_update_document_structure_real_change_still_persists(services):
    document_service = services["document_service"]
    structure = document_service.create_document_structure(
        structure_code=_unique_code("STRUCT-UPDATE"), name="Before"
    )

    updated = document_service.update_document_structure(
        structure.id, name="After", expected_version=structure.version
    )

    assert updated.name == "After"


def test_update_document_structure_no_op_produces_zero_write_zero_audit(services, monkeypatch):
    document_service = services["document_service"]
    structure = document_service.create_document_structure(
        structure_code=_unique_code("STRUCT-NOOP"), name="Same"
    )
    before = document_service._structure_repo.get(structure.id)
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = document_service.update_document_structure(
        structure.id, name="Same", expected_version=structure.version
    )

    assert result.version == structure.version
    assert audit_calls == []
    reloaded = document_service._structure_repo.get(structure.id)
    assert reloaded.version == before.version


def test_document_structure_parent_cross_org_denied(services):
    document_service = services["document_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    home_structure = document_service.create_document_structure(
        structure_code=_unique_code("STRUCT-HOME-PARENT"), name="Home Parent"
    )

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("STRUCT-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            document_service.create_document_structure(
                structure_code=_unique_code("STRUCT-CROSSORG-CHILD"),
                name="Cross Org Child",
                parent_structure_id=home_structure.id,
            )
    finally:
        tenant_context_service.set_active_organization(default_organization.id)


def test_update_document_structure_self_parent_invalid(services):
    document_service = services["document_service"]
    structure = document_service.create_document_structure(
        structure_code=_unique_code("STRUCT-SELF"), name="Self Parent"
    )

    with pytest.raises(ValidationError, match="cannot be its own parent"):
        document_service.update_document_structure(structure.id, parent_structure_id=structure.id)


def test_document_structure_audit_failure_rolls_back(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated structure audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    document_service = services["document_service"]
    code = _unique_code("STRUCT-AUDITFAIL")

    with pytest.raises(RuntimeError, match="simulated structure audit failure"):
        document_service.create_document_structure(structure_code=code, name="Audit Fail")

    monkeypatch.undo()


def test_document_structure_commit_failure_rolls_back(services, monkeypatch):
    document_service = services["document_service"]
    code = _unique_code("STRUCT-COMMITFAIL")

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        document_service.create_document_structure(structure_code=code, name="Commit Fail")


# ---------------------------------------------------------------------------
# DocumentLink (write-outcome only -- typed-event proofs live in
# test_p16d_document_link_typed_events.py)
# ---------------------------------------------------------------------------


def test_add_link_success(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("LINK-DOC"), title="Linkable", storage_uri="C:/docs/j.pdf"
    )

    link = document_service.add_link(
        document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-1"
    )

    assert link.document_id == document.id


def test_remove_link_success(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("UNLINK-DOC"), title="Linkable", storage_uri="C:/docs/k.pdf"
    )
    link = document_service.add_link(
        document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-2"
    )

    document_service.remove_link(link.id)

    assert document_service.list_links(document.id) == []


def test_add_link_duplicate_denied(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("DUPE-LINK-DOC"), title="Linkable", storage_uri="C:/docs/l.pdf"
    )
    document_service.add_link(
        document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-3"
    )

    with pytest.raises(ValidationError, match="already exists"):
        document_service.add_link(
            document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-3"
        )


def test_remove_link_missing_denied(services):
    document_service = services["document_service"]

    with pytest.raises(NotFoundError):
        document_service.remove_link("does-not-exist")


def test_add_link_cross_org_document_denied(services):
    document_service = services["document_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    document = document_service.create_document(
        document_code=_unique_code("LINK-CROSSORG-DOC"), title="Home Doc", storage_uri="C:/docs/m.pdf"
    )

    other_organization = organization_service.create_organization(
        organization_code=_unique_code("LINK-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            document_service.add_link(
                document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-4"
            )
    finally:
        tenant_context_service.set_active_organization(default_organization.id)


# ---------------------------------------------------------------------------
# DocumentIntegrationService (write-outcome/atomicity only)
# ---------------------------------------------------------------------------


def test_register_entity_attachments_uses_exactly_one_uow_session_commit(services, monkeypatch):
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    create_calls = []
    original_create = type(integration_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        create_calls.append(uow)
        return uow

    monkeypatch.setattr(type(integration_service._uow_factory), "create", _spy_create)

    integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="inventory_procurement",
        entity_type="purchase_order",
        entity_id=_unique_code("PO"),
        attachments=["C:/att/one.pdf", "C:/att/two.pdf", "C:/att/three.pdf"],
    )

    assert len(create_calls) == 1


def test_register_entity_attachments_persists_n_documents_and_n_links_atomically(services):
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    entity_id = _unique_code("PO-ATOMIC")

    created = integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="inventory_procurement",
        entity_type="purchase_order",
        entity_id=entity_id,
        attachments=["C:/att/a.pdf", "C:/att/b.pdf"],
    )

    assert len(created) == 2
    links = integration_service.list_documents_for_entity(
        required_permission="settings.manage",
        operation_label="list",
        module_code="inventory_procurement",
        entity_type="purchase_order",
        entity_id=entity_id,
    )
    assert {doc.id for doc in links} == {doc.id for doc in created}


def test_register_entity_attachments_failure_midway_rolls_back_entire_batch(services, monkeypatch):
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    entity_id = _unique_code("PO-FAIL")
    call_count = {"n": 0}
    original_record = EnterpriseAuditService.record

    def _fail_on_second(self, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated mid-batch audit failure")
        return original_record(self, **kwargs)

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_on_second)

    with pytest.raises(RuntimeError, match="simulated mid-batch audit failure"):
        integration_service.register_entity_attachments(
            required_permission="settings.manage",
            operation_label="register attachments",
            module_code="inventory_procurement",
            entity_type="purchase_order",
            entity_id=entity_id,
            attachments=["C:/att/x.pdf", "C:/att/y.pdf"],
        )

    monkeypatch.undo()
    remaining = integration_service.list_documents_for_entity(
        required_permission="settings.manage",
        operation_label="list",
        module_code="inventory_procurement",
        entity_type="purchase_order",
        entity_id=entity_id,
    )
    assert remaining == []


def test_link_existing_document_success(services):
    document_service = services["document_service"]
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    document = document_service.create_document(
        document_code=_unique_code("INT-LINK-DOC"), title="Doc", storage_uri="C:/docs/n.pdf"
    )

    link = integration_service.link_existing_document(
        required_permission="settings.manage",
        operation_label="link",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=_unique_code("ITEM"),
        document_id=document.id,
    )

    assert link.document_id == document.id


def test_unlink_existing_document_success(services):
    document_service = services["document_service"]
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    document = document_service.create_document(
        document_code=_unique_code("INT-UNLINK-DOC"), title="Doc", storage_uri="C:/docs/o.pdf"
    )
    entity_id = _unique_code("ITEM")
    integration_service.link_existing_document(
        required_permission="settings.manage",
        operation_label="link",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=entity_id,
        document_id=document.id,
    )

    integration_service.unlink_existing_document(
        required_permission="settings.manage",
        operation_label="unlink",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=entity_id,
        document_id=document.id,
    )

    assert integration_service.list_documents_for_entity(
        required_permission="settings.manage",
        operation_label="list",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=entity_id,
    ) == []


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


def test_two_independent_create_document_calls_use_genuinely_different_sessions(services, monkeypatch):
    document_service = services["document_service"]
    created_sessions = []
    original_create = type(document_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(document_service._uow_factory), "create", _spy_create)

    document_service.create_document(
        document_code=_unique_code("FRESH-A"), title="Fresh A", storage_uri="C:/docs/p.pdf"
    )
    document_service.create_document(
        document_code=_unique_code("FRESH-B"), title="Fresh B", storage_uri="C:/docs/q.pdf"
    )

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not document_service._session for s in created_sessions)


def test_create_document_repository_and_audit_share_the_uow_session(services, monkeypatch):
    document_service = services["document_service"]
    seen = {}
    original_create = type(document_service._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["documents_repo_session"] = uow.documents.session
        seen["structures_repo_session"] = uow.structures.session
        seen["links_repo_session"] = uow.links.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(document_service._uow_factory), "create", _spy_create)

    document_service.create_document(
        document_code=_unique_code("SHARE"), title="Shared Session Document", storage_uri="C:/docs/r.pdf"
    )

    assert seen["uow_session"] is seen["documents_repo_session"]
    assert seen["uow_session"] is seen["structures_repo_session"]
    assert seen["uow_session"] is seen["links_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_document_service_and_integration_service_share_the_same_uow_factory(services):
    document_service = services["document_service"]
    integration_service = services["inventory_purchasing_service"]._document_integration_service

    assert document_service._uow_factory is integration_service._uow_factory


# ---------------------------------------------------------------------------
# Architecture guards
# ---------------------------------------------------------------------------


def test_no_raw_session_commit_in_document_mutation_paths():
    import inspect

    import src.core.platform.application.master_data.documents.document_commands as document_commands
    import src.core.platform.application.master_data.documents.document_integration_service as document_integration_service

    for module in (document_commands, document_integration_service):
        source = inspect.getsource(module)
        assert "self._session.commit(" not in source
        assert "self._session.rollback(" not in source
        assert "uow.commit()" in source


def test_document_uow_uses_named_repositories_only():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.document_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "repository_for(" not in source
    assert "resolve_adapter(" not in source
    assert "container.get(" not in source
    assert "self.documents = " in source
    assert "self.structures = " in source
    assert "self.links = " in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.document_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source
