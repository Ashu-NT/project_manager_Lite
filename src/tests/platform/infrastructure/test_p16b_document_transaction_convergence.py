from __future__ import annotations

import pytest

from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.master_data.documents.dto.commands.documents import (
    DocumentCreateCommand,
    DocumentUpdateCommand,
)
from src.core.platform.application.master_data.documents.dto.commands.links import (
    DocumentLinkCreateCommand,
)
from src.core.platform.application.master_data.documents.dto.commands.structures import (
    DocumentStructureCreateCommand,
    DocumentStructureUpdateCommand,
)
from src.core.platform.common.exceptions import (
    ConcurrencyError,
    NotFoundError,
    ValidationError,
)
from src.core.platform.infrastructure.persistence.uow.master_data.document_unit_of_work import (
    SqlAlchemyDocumentUnitOfWork,
)

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


# ---------------------------------------------------------------------------
# Document (write-outcome/rollback only -- event-emission proofs live in
# test_p16c_document_typed_events.py and test_p16d_document_link_typed_events.py)
# ---------------------------------------------------------------------------


def test_create_document_still_persists(services):
    document_commands = services["document_commands"]
    code = _unique_code("DOC-CREATE")
    document = document_commands.create_document(DocumentCreateCommand(document_code=code, title="Create Ok", storage_uri="C:/docs/a.pdf"))

    assert document.document_code == code
    reloaded = services["document_query"]._document_repo.get(document.id)
    assert reloaded is not None
    assert reloaded.document_code == code


def test_update_document_real_change_still_persists(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("DOC-UPDATE"), title="Before", storage_uri="C:/docs/b.pdf"))

    updated = document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="After", expected_version=document.version))

    assert updated.title == "After"
    reloaded = services["document_query"]._document_repo.get(document.id)
    assert reloaded.title == "After"


def test_update_document_no_op_produces_zero_write_zero_audit(services, monkeypatch):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("DOC-NOOP"), title="Same", storage_uri="C:/docs/c.pdf"))
    before = services["document_query"]._document_repo.get(document.id)
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="Same", storage_uri="C:/docs/c.pdf", expected_version=document.version))

    assert result.version == document.version
    assert audit_calls == []
    reloaded = services["document_query"]._document_repo.get(document.id)
    assert reloaded.version == before.version


def test_create_document_duplicate_code_rolls_back(services):
    document_commands = services["document_commands"]
    code = _unique_code("DOC-DUPE")
    document_commands.create_document(DocumentCreateCommand(document_code=code, title="First", storage_uri="C:/docs/d.pdf"))

    with pytest.raises(ValidationError, match="Document code already exists"):
        document_commands.create_document(DocumentCreateCommand(document_code=code, title="Second", storage_uri="C:/docs/e.pdf"))


def test_update_document_cross_org_denied(services):
    document_commands = services["document_commands"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("DOC-CROSSORG"), title="Home Org Doc", storage_uri="C:/docs/f.pdf"))

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("DOC-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="Hijacked"))
    finally:
        tenant_context_service.set_active_organization(default_organization.id)


def test_update_document_stale_version_raises(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("DOC-STALE"), title="Stale Doc", storage_uri="C:/docs/g.pdf"))

    with pytest.raises(ConcurrencyError):
        document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="Should Not Apply", expected_version=document.version + 1))


def test_create_document_audit_failure_rolls_back(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated document audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    document_commands = services["document_commands"]
    code = _unique_code("DOC-AUDITFAIL")

    with pytest.raises(RuntimeError, match="simulated document audit failure"):
        document_commands.create_document(DocumentCreateCommand(document_code=code, title="Audit Fail", storage_uri="C:/docs/h.pdf"))

    monkeypatch.undo()
    organization = services["document_query"]._tenant_context_service.get_active_organization()
    assert services["document_query"]._document_repo.get_by_code(organization.id, code) is None


def test_create_document_commit_failure_rolls_back(services, monkeypatch):
    document_commands = services["document_commands"]
    code = _unique_code("DOC-COMMITFAIL")

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        document_commands.create_document(DocumentCreateCommand(document_code=code, title="Commit Fail", storage_uri="C:/docs/i.pdf"))


# ---------------------------------------------------------------------------
# DocumentStructure
# ---------------------------------------------------------------------------


def test_create_document_structure_still_persists(services):
    document_structure_commands = services["document_structure_commands"]
    code = _unique_code("STRUCT-CREATE")

    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=code, name="Manuals"))

    assert structure.structure_code == code.replace("-", "_")


def test_update_document_structure_real_change_still_persists(services):
    document_structure_commands = services["document_structure_commands"]
    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("STRUCT-UPDATE"), name="Before"))

    updated = document_structure_commands.update_document_structure(DocumentStructureUpdateCommand(structure_id=structure.id, name="After", expected_version=structure.version))

    assert updated.name == "After"


def test_update_document_structure_no_op_produces_zero_write_zero_audit(services, monkeypatch):
    document_structure_commands = services["document_structure_commands"]
    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("STRUCT-NOOP"), name="Same"))
    before = services["document_query"]._structure_repo.get(structure.id)
    audit_calls = []
    monkeypatch.setattr(
        EnterpriseAuditService, "record", lambda self, **kwargs: audit_calls.append(kwargs)
    )

    result = document_structure_commands.update_document_structure(DocumentStructureUpdateCommand(structure_id=structure.id, name="Same", expected_version=structure.version))

    assert result.version == structure.version
    assert audit_calls == []
    reloaded = services["document_query"]._structure_repo.get(structure.id)
    assert reloaded.version == before.version


def test_document_structure_parent_cross_org_denied(services):
    document_structure_commands = services["document_structure_commands"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    home_structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("STRUCT-HOME-PARENT"), name="Home Parent"))

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("STRUCT-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("STRUCT-CROSSORG-CHILD"), name="Cross Org Child", parent_structure_id=home_structure.id))
    finally:
        tenant_context_service.set_active_organization(default_organization.id)


def test_update_document_structure_self_parent_invalid(services):
    document_structure_commands = services["document_structure_commands"]
    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("STRUCT-SELF"), name="Self Parent"))

    with pytest.raises(ValidationError, match="cannot be its own parent"):
        document_structure_commands.update_document_structure(DocumentStructureUpdateCommand(structure_id=structure.id, parent_structure_id=structure.id))


def test_document_structure_audit_failure_rolls_back(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated structure audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    document_structure_commands = services["document_structure_commands"]
    code = _unique_code("STRUCT-AUDITFAIL")

    with pytest.raises(RuntimeError, match="simulated structure audit failure"):
        document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=code, name="Audit Fail"))

    monkeypatch.undo()


def test_document_structure_commit_failure_rolls_back(services, monkeypatch):
    document_structure_commands = services["document_structure_commands"]
    code = _unique_code("STRUCT-COMMITFAIL")

    def _fail_commit(self):
        raise RuntimeError("simulated database commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=code, name="Commit Fail"))


# ---------------------------------------------------------------------------
# DocumentLink (write-outcome only -- typed-event proofs live in
# test_p16d_document_link_typed_events.py)
# ---------------------------------------------------------------------------


def test_add_link_success(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("LINK-DOC"), title="Linkable", storage_uri="C:/docs/j.pdf"))

    link = document_commands.add_link(DocumentLinkCreateCommand(document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-1"))

    assert link.document_id == document.id


def test_remove_link_success(services):
    document_commands = services["document_commands"]
    document_query = services["document_query"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("UNLINK-DOC"), title="Linkable", storage_uri="C:/docs/k.pdf"))
    link = document_commands.add_link(DocumentLinkCreateCommand(document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-2"))

    document_commands.remove_link(link.id)

    assert document_query.list_links(document.id) == []


def test_add_link_duplicate_denied(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("DUPE-LINK-DOC"), title="Linkable", storage_uri="C:/docs/l.pdf"))
    document_commands.add_link(DocumentLinkCreateCommand(document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-3"))

    with pytest.raises(ValidationError, match="already exists"):
        document_commands.add_link(DocumentLinkCreateCommand(document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-3"))


def test_remove_link_missing_denied(services):
    document_commands = services["document_commands"]

    with pytest.raises(NotFoundError):
        document_commands.remove_link("does-not-exist")


def test_add_link_cross_org_document_denied(services):
    document_commands = services["document_commands"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("LINK-CROSSORG-DOC"), title="Home Doc", storage_uri="C:/docs/m.pdf"))

    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("LINK-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    try:
        with pytest.raises(NotFoundError):
            document_commands.add_link(DocumentLinkCreateCommand(document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-4"))
    finally:
        tenant_context_service.set_active_organization(default_organization.id)


# ---------------------------------------------------------------------------
# Document attachment handlers (write-outcome/atomicity only)
# ---------------------------------------------------------------------------


def test_register_entity_attachments_uses_exactly_one_uow_session_commit(services, monkeypatch):
    integration_service = services["document_attachment_commands"]
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
        module_code="project_management",
        entity_type="attachment_batch",
        entity_id=_unique_code("PO"),
        attachments=["C:/att/one.pdf", "C:/att/two.pdf", "C:/att/three.pdf"],
    )

    assert len(create_calls) == 1


def test_register_entity_attachments_persists_n_documents_and_n_links_atomically(services):
    integration_service = services["document_attachment_commands"]
    entity_id = _unique_code("PO-ATOMIC")

    created = integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="project_management",
        entity_type="attachment_batch",
        entity_id=entity_id,
        attachments=["C:/att/a.pdf", "C:/att/b.pdf"],
    )

    assert len(created) == 2
    links = services["document_attachment_query"].list_documents_for_entity(
        required_permission="settings.manage",
        operation_label="list",
        module_code="project_management",
        entity_type="attachment_batch",
        entity_id=entity_id,
    )
    assert {doc.id for doc in links} == {doc.id for doc in created}


def test_register_entity_attachments_failure_midway_rolls_back_entire_batch(services, monkeypatch):
    integration_service = services["document_attachment_commands"]
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
            module_code="project_management",
            entity_type="attachment_batch",
            entity_id=entity_id,
            attachments=["C:/att/x.pdf", "C:/att/y.pdf"],
        )

    monkeypatch.undo()
    remaining = services["document_attachment_query"].list_documents_for_entity(
        required_permission="settings.manage",
        operation_label="list",
        module_code="project_management",
        entity_type="attachment_batch",
        entity_id=entity_id,
    )
    assert remaining == []


def test_link_existing_document_success(services):
    document_commands = services["document_commands"]
    integration_service = services["document_attachment_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("INT-LINK-DOC"), title="Doc", storage_uri="C:/docs/n.pdf"))

    link = integration_service.link_existing_document(
        required_permission="settings.manage",
        operation_label="link",
        module_code="project_management",
        entity_type="task",
        entity_id=_unique_code("ITEM"),
        document_id=document.id,
    )

    assert link.document_id == document.id


def test_unlink_existing_document_success(services):
    document_commands = services["document_commands"]
    integration_service = services["document_attachment_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("INT-UNLINK-DOC"), title="Doc", storage_uri="C:/docs/o.pdf"))
    entity_id = _unique_code("ITEM")
    integration_service.link_existing_document(
        required_permission="settings.manage",
        operation_label="link",
        module_code="project_management",
        entity_type="task",
        entity_id=entity_id,
        document_id=document.id,
    )

    integration_service.unlink_existing_document(
        required_permission="settings.manage",
        operation_label="unlink",
        module_code="project_management",
        entity_type="task",
        entity_id=entity_id,
        document_id=document.id,
    )

    assert services["document_attachment_query"].list_documents_for_entity(
        required_permission="settings.manage",
        operation_label="list",
        module_code="project_management",
        entity_type="task",
        entity_id=entity_id,
    ) == []


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------


def test_two_independent_create_document_calls_use_genuinely_different_sessions(services, monkeypatch):
    document_commands = services["document_commands"]
    created_sessions = []
    original_create = type(services["document_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        created_sessions.append(uow._session)
        return uow

    monkeypatch.setattr(type(services["document_commands"]._uow_factory), "create", _spy_create)

    document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("FRESH-A"), title="Fresh A", storage_uri="C:/docs/p.pdf"))
    document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("FRESH-B"), title="Fresh B", storage_uri="C:/docs/q.pdf"))

    assert len(created_sessions) == 2
    assert created_sessions[0] is not created_sessions[1]
    assert all(s is not services["session"] for s in created_sessions)


def test_create_document_repository_and_audit_share_the_uow_session(services, monkeypatch):
    document_commands = services["document_commands"]
    seen = {}
    original_create = type(services["document_commands"]._uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen["uow_session"] = uow._session
        seen["documents_repo_session"] = uow.documents.session
        seen["structures_repo_session"] = uow.structures.session
        seen["links_repo_session"] = uow.links.session
        seen["audit_session"] = uow._enterprise_audit_service._session
        return uow

    monkeypatch.setattr(type(services["document_commands"]._uow_factory), "create", _spy_create)

    document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("SHARE"), title="Shared Session Document", storage_uri="C:/docs/r.pdf"))

    assert seen["uow_session"] is seen["documents_repo_session"]
    assert seen["uow_session"] is seen["structures_repo_session"]
    assert seen["uow_session"] is seen["links_repo_session"]
    assert seen["uow_session"] is seen["audit_session"]


def test_document_service_and_integration_service_share_the_same_uow_factory(services):
    integration_service = services["document_attachment_commands"]

    assert services["document_commands"]._uow_factory is integration_service._uow_factory


# ---------------------------------------------------------------------------
# Architecture guards
# ---------------------------------------------------------------------------


def test_no_raw_session_commit_in_document_mutation_paths():
    import inspect

    from src.core.platform.application.master_data.documents.commands import (
        document_attachment_commands,
        document_commands,
        document_structure_commands,
    )

    for module in (document_commands, document_structure_commands, document_attachment_commands):
        source = inspect.getsource(module)
        assert "self._session.commit(" not in source
        assert "self._session.rollback(" not in source
        assert "uow.commit()" in source


def test_document_uow_uses_named_repositories_only():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.master_data.document_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "repository_for(" not in source
    assert "resolve_adapter(" not in source
    assert "container.get(" not in source
    assert "self.documents = " in source
    assert "self.structures = " in source
    assert "self.links = " in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.master_data.document_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source
