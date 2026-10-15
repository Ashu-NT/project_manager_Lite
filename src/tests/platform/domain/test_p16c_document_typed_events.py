from __future__ import annotations

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.application.master_data.documents.dto.commands.documents import (
    DocumentCreateCommand,
    DocumentUpdateCommand,
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
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentProfileUpdated,
    DocumentStructureCreated,
    DocumentStructureProfileUpdated,
)
from src.core.platform.infrastructure.persistence.uow.master_data.document_unit_of_work import (
    SqlAlchemyDocumentUnitOfWork,
)
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy_event(services, event_type, *, on="document_commands"):
    calls = []
    services[on]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def _spy_document_list_hints(services):
    from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
        DOCUMENT_CATEGORY,
        DOCUMENT_LIST_SCOPE_CODE,
    )
    from src.core.shared.events.view_invalidation import ExactOrganization

    organization = services["tenant_context_service"].get_active_organization()
    hints = []

    def _on_hint(hint):
        if hint.category == DOCUMENT_CATEGORY and hint.scope_code == DOCUMENT_LIST_SCOPE_CODE:
            hints.append(hint)

    services["platform_view_invalidation_channel"].subscribe(
        ExactOrganization(organization.tenant_id, organization.id), _on_hint
    )
    return hints


def _spy_document_structure_list_hints(services):
    from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
        DOCUMENT_STRUCTURE_CATEGORY,
        DOCUMENT_STRUCTURE_LIST_SCOPE_CODE,
    )
    from src.core.shared.events.view_invalidation import ExactOrganization

    organization = services["tenant_context_service"].get_active_organization()
    hints = []

    def _on_hint(hint):
        if hint.category == DOCUMENT_STRUCTURE_CATEGORY and hint.scope_code == DOCUMENT_STRUCTURE_LIST_SCOPE_CODE:
            hints.append(hint)

    services["platform_view_invalidation_channel"].subscribe(
        ExactOrganization(organization.tenant_id, organization.id), _on_hint
    )
    return hints


def _platform_catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


# ---------------------------------------------------------------------------
# Business events: Document
# ---------------------------------------------------------------------------


def test_create_document_produces_exactly_one_document_created(services):
    calls = _spy_event(services, DocumentCreated)
    document = services["document_commands"].create_document(DocumentCreateCommand(document_code=_unique_code("P16C-CREATE"), title="Create Ok", storage_uri="C:/docs/a.pdf"))
    assert [e.document_id for e in calls] == [document.id]
    assert calls[0].organization_id == document.organization_id


def test_real_update_document_produces_exactly_one_document_profile_updated(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-UPDATE"), title="Before", storage_uri="C:/docs/b.pdf"))
    calls = _spy_event(services, DocumentProfileUpdated)

    document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="After", expected_version=document.version))

    assert len(calls) == 1
    assert calls[0].document_id == document.id


def test_no_op_document_update_produces_zero_event(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-NOOP"), title="Same", storage_uri="C:/docs/c.pdf"))
    calls = _spy_event(services, DocumentProfileUpdated)

    document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="Same", storage_uri="C:/docs/c.pdf", expected_version=document.version))

    assert calls == []


def test_document_authorization_failure_produces_zero_event(services, monkeypatch):
    document_commands = services["document_commands"]
    calls = _spy_event(services, DocumentCreated)

    def _deny(*args, **kwargs):
        raise ValidationError("denied", code="PERMISSION_DENIED")

    monkeypatch.setattr(
        "src.core.platform.application.master_data.documents.commands.document_commands.require_permission",
        _deny,
    )

    with pytest.raises(ValidationError):
        document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-AUTHFAIL"), title="No Access", storage_uri="C:/docs/d.pdf"))

    assert calls == []


def test_document_cross_org_update_produces_zero_event(services):
    document_commands = services["document_commands"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-CROSSORG"), title="Home Doc", storage_uri="C:/docs/e.pdf"))
    other_organization = services["organization_commands"].create_organization(
        organization_code=_unique_code("P16C-CROSSORG-OTHER"),
        display_name="Other Org",
        timezone_name="UTC",
        base_currency="USD",
    )
    tenant_context_service.set_active_organization(other_organization.id)
    calls = _spy_event(services, DocumentProfileUpdated)
    try:
        with pytest.raises(NotFoundError):
            document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="Hijacked"))
    finally:
        tenant_context_service.set_active_organization(default_organization.id)

    assert calls == []


def test_document_stale_version_produces_zero_event(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-STALE"), title="Stale Doc", storage_uri="C:/docs/f.pdf"))
    calls = _spy_event(services, DocumentProfileUpdated)

    with pytest.raises(ConcurrencyError):
        document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="Should Not Apply", expected_version=document.version + 1))

    assert calls == []


def test_document_audit_failure_produces_zero_event(services, monkeypatch):
    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)
    document_commands = services["document_commands"]
    calls = _spy_event(services, DocumentCreated)

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-AUDITFAIL"), title="Audit Fail", storage_uri="C:/docs/g.pdf"))

    monkeypatch.undo()
    assert calls == []


def test_document_commit_failure_produces_zero_event(services, monkeypatch):
    document_commands = services["document_commands"]
    calls = _spy_event(services, DocumentCreated)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-COMMITFAIL"), title="Commit Fail", storage_uri="C:/docs/h.pdf"))

    assert calls == []


# ---------------------------------------------------------------------------
# Business events: DocumentStructure
# ---------------------------------------------------------------------------


def test_create_structure_produces_exactly_one_document_structure_created(services):
    calls = _spy_event(services, DocumentStructureCreated)
    structure = services["document_structure_commands"].create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-STRUCT-CREATE"), name="Manuals"))
    assert [e.structure_id for e in calls] == [structure.id]


def test_real_structure_update_produces_exactly_one_document_structure_profile_updated(services):
    document_structure_commands = services["document_structure_commands"]
    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-STRUCT-UPDATE"), name="Before"))
    calls = _spy_event(services, DocumentStructureProfileUpdated)

    document_structure_commands.update_document_structure(DocumentStructureUpdateCommand(structure_id=structure.id, name="After", expected_version=structure.version))

    assert len(calls) == 1
    assert calls[0].structure_id == structure.id


def test_no_op_structure_update_produces_zero_event(services):
    document_structure_commands = services["document_structure_commands"]
    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-STRUCT-NOOP"), name="Same"))
    calls = _spy_event(services, DocumentStructureProfileUpdated)

    document_structure_commands.update_document_structure(DocumentStructureUpdateCommand(structure_id=structure.id, name="Same", expected_version=structure.version))

    assert calls == []


def test_structure_commit_failure_produces_zero_event(services, monkeypatch):
    document_structure_commands = services["document_structure_commands"]
    calls = _spy_event(services, DocumentStructureCreated)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-STRUCT-COMMITFAIL"), name="Fail"))

    assert calls == []


# ---------------------------------------------------------------------------
# document_list / document_structure_list ViewInvalidation dedup
# ---------------------------------------------------------------------------


def test_two_separate_document_commits_produce_exactly_two_document_list_hints(services):
    document_commands = services["document_commands"]
    hints = _spy_document_list_hints(services)

    document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-SEP-A"), title="A", storage_uri="C:/docs/i.pdf"))
    document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-SEP-B"), title="B", storage_uri="C:/docs/j.pdf"))

    assert len(hints) == 2


def test_two_separate_structure_commits_produce_exactly_two_document_structure_list_hints(services):
    document_structure_commands = services["document_structure_commands"]
    hints = _spy_document_structure_list_hints(services)

    document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-STRUCT-SEP-A"), name="A"))
    document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-STRUCT-SEP-B"), name="B"))

    assert len(hints) == 2


def test_failed_document_commit_produces_zero_document_list_hints(services, monkeypatch):
    document_commands = services["document_commands"]
    hints = _spy_document_list_hints(services)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-HINT-FAIL"), title="Fail", storage_uri="C:/docs/k.pdf"))

    assert hints == []


# ---------------------------------------------------------------------------
# Batch attachments (register_entity_attachments)
# ---------------------------------------------------------------------------


def test_register_entity_attachments_produces_n_document_created_business_events(services):
    integration_service = services["document_attachment_commands"]
    calls = _spy_event(services, DocumentCreated, on="document_commands")
    entity_id = _unique_code("P16C-BATCH")

    created = integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="project_management",
        entity_type="purchase_order",
        entity_id=entity_id,
        attachments=["C:/att/one.pdf", "C:/att/two.pdf", "C:/att/three.pdf"],
    )

    assert len(created) == 3
    assert {e.document_id for e in calls} == {doc.id for doc in created}


def test_register_entity_attachments_uses_one_transaction_for_all_typed_events(services, monkeypatch):
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
        entity_type="purchase_order",
        entity_id=_unique_code("P16C-BATCH-TXN"),
        attachments=["C:/att/x.pdf", "C:/att/y.pdf"],
    )

    assert len(create_calls) == 1


def test_register_entity_attachments_coalesces_to_one_document_list_hint(services):
    integration_service = services["document_attachment_commands"]
    hints = _spy_document_list_hints(services)

    integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="project_management",
        entity_type="purchase_order",
        entity_id=_unique_code("P16C-BATCH-COALESCE"),
        attachments=["C:/att/p.pdf", "C:/att/q.pdf", "C:/att/r.pdf", "C:/att/s.pdf"],
    )

    assert len(hints) == 1


# ---------------------------------------------------------------------------
# UI: Admin narrow refresh
# ---------------------------------------------------------------------------


def test_admin_document_controller_refreshes_once_after_committed_create(services):
    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documents

    refresh_calls = []
    catalog.adminWorkspace._document_controller.refresh = (
        lambda: refresh_calls.append("admin-documents") or None
    )
    full_refresh_calls = []
    catalog.adminWorkspace.refresh = lambda: full_refresh_calls.append("full") or None

    services["document_commands"].create_document(DocumentCreateCommand(document_code=_unique_code("P16C-ADMIN-CREATE"), title="Admin Refresh Doc", storage_uri="C:/docs/l.pdf"))

    assert refresh_calls == ["admin-documents"]
    assert full_refresh_calls == []


def test_admin_document_controller_refreshes_once_after_real_update(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-ADMIN-UPDATE"), title="Before", storage_uri="C:/docs/m.pdf"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documents

    refresh_calls = []
    catalog.adminWorkspace._document_controller.refresh = (
        lambda: refresh_calls.append("admin-documents") or None
    )

    document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="After", expected_version=document.version))

    assert refresh_calls == ["admin-documents"]


def test_admin_document_controller_no_refresh_on_no_op(services):
    document_commands = services["document_commands"]
    document = document_commands.create_document(DocumentCreateCommand(document_code=_unique_code("P16C-ADMIN-NOOP"), title="Same", storage_uri="C:/docs/n.pdf"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documents

    refresh_calls = []
    catalog.adminWorkspace._document_controller.refresh = (
        lambda: refresh_calls.append("admin-documents") or None
    )

    document_commands.update_document(DocumentUpdateCommand(document_id=document.id, title="Same", expected_version=document.version))

    assert refresh_calls == []


def test_admin_document_controller_no_refresh_on_failed_transaction(services):
    document_commands = services["document_commands"]
    code = _unique_code("P16C-ADMIN-FAILED")
    document_commands.create_document(DocumentCreateCommand(document_code=code, title="Existing", storage_uri="C:/docs/o.pdf"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documents

    refresh_calls = []
    catalog.adminWorkspace._document_controller.refresh = (
        lambda: refresh_calls.append("admin-documents") or None
    )

    with pytest.raises(ValidationError):
        document_commands.create_document(DocumentCreateCommand(document_code=code, title="Duplicate", storage_uri="C:/docs/p.pdf"))

    assert refresh_calls == []


def test_admin_structure_controller_refreshes_once_after_committed_create(services):
    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documentStructures

    refresh_calls = []
    catalog.adminWorkspace._document_structure_controller.refresh = (
        lambda: refresh_calls.append("admin-structures") or None
    )
    full_refresh_calls = []
    catalog.adminWorkspace.refresh = lambda: full_refresh_calls.append("full") or None

    services["document_structure_commands"].create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-ADMIN-STRUCT-CREATE"), name="Admin Refresh Structure"))

    assert refresh_calls == ["admin-structures"]
    assert full_refresh_calls == []


def test_admin_structure_controller_refreshes_once_after_real_update(services):
    document_structure_commands = services["document_structure_commands"]
    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-ADMIN-STRUCT-UPDATE"), name="Before"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documentStructures

    refresh_calls = []
    catalog.adminWorkspace._document_structure_controller.refresh = (
        lambda: refresh_calls.append("admin-structures") or None
    )

    document_structure_commands.update_document_structure(DocumentStructureUpdateCommand(structure_id=structure.id, name="After", expected_version=structure.version))

    assert refresh_calls == ["admin-structures"]


def test_admin_structure_controller_no_refresh_on_no_op(services):
    document_structure_commands = services["document_structure_commands"]
    structure = document_structure_commands.create_document_structure(DocumentStructureCreateCommand(structure_code=_unique_code("P16C-ADMIN-STRUCT-NOOP"), name="Same"))

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documentStructures

    refresh_calls = []
    catalog.adminWorkspace._document_structure_controller.refresh = (
        lambda: refresh_calls.append("admin-structures") or None
    )

    document_structure_commands.update_document_structure(DocumentStructureUpdateCommand(structure_id=structure.id, name="Same", expected_version=structure.version))

    assert refresh_calls == []


# ---------------------------------------------------------------------------
# Architecture guards
# ---------------------------------------------------------------------------


def test_no_blanket_document_changed_or_document_updated_event_exists():
    import glob
    import re

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if re.search(r"\bDocumentChanged\b", source) or (
            re.search(r"\bDocumentUpdated\b", source) and "DocumentProfileUpdated" not in source
        ):
            hits.append(normalized)
    assert hits == [], hits


def test_document_list_view_invalidation_handler_has_no_generic_bridge():
    import inspect

    import src.core.platform.application.master_data.documents.event_handlers.view_invalidation as vi_module

    source = inspect.getsource(vi_module)
    assert "getattr(domain_events" not in source


def test_no_documents_changed_reference_in_simple_document_and_structure_paths():
    import inspect

    from src.core.platform.application.master_data.documents import (
        DocumentCommandHandler,
        DocumentStructureCommandHandler,
    )

    create_document_source = inspect.getsource(DocumentCommandHandler.create_document)
    update_document_source = inspect.getsource(DocumentCommandHandler.update_document)
    create_structure_source = inspect.getsource(DocumentStructureCommandHandler.create_document_structure)
    update_structure_source = inspect.getsource(DocumentStructureCommandHandler.update_document_structure)

    for source in (
        create_document_source,
        update_document_source,
        create_structure_source,
        update_structure_source,
    ):
        assert "documents_changed" not in source


def test_no_raw_session_commit_reintroduced():
    import inspect

    import src.core.platform.application.master_data.documents.commands.document_attachment_commands as document_integration_service_module
    import src.core.platform.application.master_data.documents.commands.document_commands as document_commands_module

    for module in (document_commands_module, document_integration_service_module):
        source = inspect.getsource(module)
        assert "self._session.commit(" not in source
        assert "self._session.rollback(" not in source


def test_canonical_document_uow_retained():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.master_data.document_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "class SqlAlchemyDocumentUnitOfWork(" in source
    assert "self.documents = " in source
    assert "self.structures = " in source
    assert "self.links = " in source
