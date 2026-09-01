from __future__ import annotations

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.history.audit.enterprise_audit_service import (
    EnterpriseAuditService,
)
from src.core.platform.common.exceptions import NotFoundError, ValidationError
from src.core.platform.domain.master_data.documents.events import (
    DocumentCreated,
    DocumentReferenceLinked,
    DocumentReferenceUnlinked,
)
from src.core.platform.infrastructure.persistence.uow.document_unit_of_work import (
    SqlAlchemyDocumentUnitOfWork,
)
from src.core.shared.events.domain_events import domain_events
from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

_COUNTER = {"n": 0}


def _unique_code(prefix: str) -> str:
    _COUNTER["n"] += 1
    return f"{prefix}-{_COUNTER['n']}"


def _spy_event(services, event_type):
    calls = []
    services["document_service"]._uow_factory._post_commit_bus.subscribe(
        event_type, lambda event, context: calls.append(event)
    )
    return calls


def _spy_document_links_hints(services):
    from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
        DOCUMENT_CATEGORY,
        DOCUMENT_LINKS_SCOPE_CODE,
    )
    from src.core.shared.events.view_invalidation import ExactOrganization

    organization = services["tenant_context_service"].get_active_organization()
    hints = []

    def _on_hint(hint):
        if hint.category == DOCUMENT_CATEGORY and hint.scope_code == DOCUMENT_LINKS_SCOPE_CODE:
            hints.append(hint)

    services["platform_view_invalidation_channel"].subscribe(
        ExactOrganization(organization.tenant_id, organization.id), _on_hint
    )
    return hints


def _platform_catalog(services) -> PlatformWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return PlatformWorkspaceCatalog(desktop_api_registry=registry)


def _inventory_catalog(services) -> InventoryProcurementWorkspaceCatalog:
    registry = build_desktop_api_registry(services)
    return InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)


# ---------------------------------------------------------------------------
# Business events
# ---------------------------------------------------------------------------


def test_add_link_produces_exactly_one_document_reference_linked(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-ADDLINK"), title="Doc", storage_uri="C:/docs/a.pdf"
    )
    calls = _spy_event(services, DocumentReferenceLinked)

    document_service.add_link(
        document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-1"
    )

    assert len(calls) == 1
    event = calls[0]
    assert event.document_id == document.id
    assert event.module_code == "qhse"
    assert event.entity_type == "inspection"
    assert event.entity_id == "insp-1"


def test_remove_link_produces_exactly_one_document_reference_unlinked(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-REMOVELINK"), title="Doc", storage_uri="C:/docs/b.pdf"
    )
    link = document_service.add_link(
        document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-2"
    )
    calls = _spy_event(services, DocumentReferenceUnlinked)

    document_service.remove_link(link.id)

    assert len(calls) == 1
    assert calls[0].document_id == document.id


def test_link_existing_document_produces_exactly_one_event(services):
    document_service = services["document_service"]
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    document = document_service.create_document(
        document_code=_unique_code("P16D-LINKEXIST"), title="Doc", storage_uri="C:/docs/c.pdf"
    )
    calls = _spy_event(services, DocumentReferenceLinked)

    integration_service.link_existing_document(
        required_permission="settings.manage",
        operation_label="link",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=_unique_code("ITEM"),
        document_id=document.id,
    )

    assert len(calls) == 1


def test_unlink_existing_document_produces_exactly_one_event(services):
    document_service = services["document_service"]
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    document = document_service.create_document(
        document_code=_unique_code("P16D-UNLINKEXIST"), title="Doc", storage_uri="C:/docs/d.pdf"
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
    calls = _spy_event(services, DocumentReferenceUnlinked)

    integration_service.unlink_existing_document(
        required_permission="settings.manage",
        operation_label="unlink",
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=entity_id,
        document_id=document.id,
    )

    assert len(calls) == 1


def test_add_link_duplicate_produces_zero_event(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-DUPE"), title="Doc", storage_uri="C:/docs/e.pdf"
    )
    document_service.add_link(
        document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-3"
    )
    calls = _spy_event(services, DocumentReferenceLinked)

    with pytest.raises(ValidationError):
        document_service.add_link(
            document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-3"
        )

    assert calls == []


def test_add_link_commit_failure_produces_zero_event(services, monkeypatch):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-LINKCOMMITFAIL"), title="Doc", storage_uri="C:/docs/f.pdf"
    )
    calls = _spy_event(services, DocumentReferenceLinked)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        document_service.add_link(
            document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-4"
        )

    assert calls == []


def test_add_link_audit_failure_produces_zero_event(services, monkeypatch):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-LINKAUDITFAIL"), title="Doc", storage_uri="C:/docs/g.pdf"
    )
    calls = _spy_event(services, DocumentReferenceLinked)

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)

    with pytest.raises(RuntimeError, match="simulated audit failure"):
        document_service.add_link(
            document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="insp-5"
        )

    monkeypatch.undo()
    assert calls == []


def test_remove_link_missing_produces_zero_event(services):
    document_service = services["document_service"]
    calls = _spy_event(services, DocumentReferenceUnlinked)

    with pytest.raises(NotFoundError):
        document_service.remove_link("does-not-exist")

    assert calls == []


# ---------------------------------------------------------------------------
# Batch attachments (register_entity_attachments, N >= 3)
# ---------------------------------------------------------------------------


def test_register_entity_attachments_produces_n_created_and_n_linked_events(services):
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    created_calls = _spy_event(services, DocumentCreated)
    linked_calls = _spy_event(services, DocumentReferenceLinked)
    entity_id = _unique_code("P16D-BATCH")

    created = integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="inventory_procurement",
        entity_type="purchase_order",
        entity_id=entity_id,
        attachments=["C:/att/1.pdf", "C:/att/2.pdf", "C:/att/3.pdf"],
    )

    assert len(created) == 3
    assert len(created_calls) == 3
    assert len(linked_calls) == 3
    assert {e.document_id for e in linked_calls} == {doc.id for doc in created}
    assert all(e.entity_id == entity_id for e in linked_calls)


def test_register_entity_attachments_failure_midway_produces_zero_events(services, monkeypatch):
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    created_calls = _spy_event(services, DocumentCreated)
    linked_calls = _spy_event(services, DocumentReferenceLinked)
    call_count = {"n": 0}
    original_record = EnterpriseAuditService.record

    def _fail_on_second(self, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise RuntimeError("simulated mid-batch failure")
        return original_record(self, **kwargs)

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_on_second)

    with pytest.raises(RuntimeError, match="simulated mid-batch failure"):
        integration_service.register_entity_attachments(
            required_permission="settings.manage",
            operation_label="register attachments",
            module_code="inventory_procurement",
            entity_type="purchase_order",
            entity_id=_unique_code("P16D-BATCH-FAIL"),
            attachments=["C:/att/x.pdf", "C:/att/y.pdf", "C:/att/z.pdf"],
        )

    monkeypatch.undo()
    assert created_calls == []
    assert linked_calls == []


# ---------------------------------------------------------------------------
# Link-scoped ViewInvalidation: dedup and per-target correctness
# ---------------------------------------------------------------------------


def test_link_entity_a_does_not_invalidate_entity_b(services):
    document_service = services["document_service"]
    doc_a = document_service.create_document(
        document_code=_unique_code("P16D-SCOPE-A"), title="Doc A", storage_uri="C:/docs/h.pdf"
    )
    hints = _spy_document_links_hints(services)

    document_service.add_link(
        document_id=doc_a.id, module_code="qhse", entity_type="inspection", entity_id="entity-a"
    )

    entity_shape_hints = [h for h in hints if h.entity_type == "inspection"]
    assert len(entity_shape_hints) == 1
    assert entity_shape_hints[0].entity_id == "entity-a"
    assert not any(h.entity_type == "inspection" and h.entity_id == "entity-b" for h in hints)


def test_n_links_to_same_entity_in_one_commit_produce_one_link_invalidation(services):
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    hints = _spy_document_links_hints(services)
    entity_id = _unique_code("P16D-SAME-ENTITY")

    integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="inventory_procurement",
        entity_type="purchase_order",
        entity_id=entity_id,
        attachments=["C:/att/m.pdf", "C:/att/n.pdf", "C:/att/o.pdf"],
    )

    entity_shape_hints = [
        h for h in hints if h.entity_type == "purchase_order" and h.entity_id == entity_id
    ]
    assert len(entity_shape_hints) == 1


def test_n_links_to_same_entity_produce_n_distinct_document_shape_hints(services):
    integration_service = services["inventory_purchasing_service"]._document_integration_service
    hints = _spy_document_links_hints(services)
    entity_id = _unique_code("P16D-DOC-SHAPE")

    created = integration_service.register_entity_attachments(
        required_permission="settings.manage",
        operation_label="register attachments",
        module_code="inventory_procurement",
        entity_type="purchase_order",
        entity_id=entity_id,
        attachments=["C:/att/p.pdf", "C:/att/q.pdf", "C:/att/r.pdf"],
    )

    document_shape_hints = [h for h in hints if h.entity_type == "document"]
    assert {h.entity_id for h in document_shape_hints} == {doc.id for doc in created}


def test_two_separate_link_commits_to_different_entities_produce_two_invalidations(services):
    document_service = services["document_service"]
    doc = document_service.create_document(
        document_code=_unique_code("P16D-TWO-ENTITIES"), title="Doc", storage_uri="C:/docs/i.pdf"
    )
    hints = _spy_document_links_hints(services)

    document_service.add_link(
        document_id=doc.id, module_code="qhse", entity_type="inspection", entity_id="two-a"
    )
    document_service.add_link(
        document_id=doc.id, module_code="qhse", entity_type="inspection", entity_id="two-b"
    )

    entity_shape_hints = [h for h in hints if h.entity_type == "inspection"]
    assert {h.entity_id for h in entity_shape_hints} == {"two-a", "two-b"}


def test_failed_link_commit_produces_zero_document_links_hints(services, monkeypatch):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-HINT-FAIL"), title="Doc", storage_uri="C:/docs/j.pdf"
    )
    hints = _spy_document_links_hints(services)

    def _fail_commit(self):
        raise RuntimeError("simulated commit failure")

    monkeypatch.setattr(SqlAlchemyDocumentUnitOfWork, "commit", _fail_commit)

    with pytest.raises(RuntimeError, match="simulated commit failure"):
        document_service.add_link(
            document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="hint-fail"
        )

    assert hints == []


def test_link_scope_is_typed_not_stringly_encoded():
    """The forward-shape hint's identity lives in three separate typed fields
    (module_code/entity_type/entity_id), never joined into one opaque string like
    'inventory:item:123' (P16D §3)."""
    from src.core.platform.application.master_data.documents.event_handlers.view_invalidation import (
        build_document_links_view_invalidation_handler,
    )
    from src.core.shared.events.domain_event_context import DomainEventContext
    from src.core.shared.events.view_invalidation import ViewInvalidationHint

    captured: list[ViewInvalidationHint] = []
    handler = build_document_links_view_invalidation_handler(channel=type("C", (), {"notify": staticmethod(captured.append)})())
    handler(
        DocumentReferenceLinked(
            tenant_id="tenant-1",
            organization_id="org-1",
            document_id="doc-1",
            module_code="inventory_procurement",
            entity_type="stock_item",
            entity_id="item-1",
            link_role="reference",
            occurred_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        ),
        DomainEventContext(correlation_id="corr-1", causation_id=None),
    )

    entity_hint = next(h for h in captured if h.entity_type == "stock_item")
    assert entity_hint.module_code == "inventory_procurement"
    assert entity_hint.entity_id == "item-1"
    assert ":" not in (entity_hint.entity_id or "")
    assert not isinstance(entity_hint.entity_id, dict)


# ---------------------------------------------------------------------------
# UI: Catalog
# ---------------------------------------------------------------------------


def test_catalog_selected_item_link_refreshes_linked_documents_narrowly(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-CATALOG-DOC"), title="Doc", storage_uri="C:/docs/k.pdf"
    )
    item_id = _unique_code("P16D-CATALOG-ITEM")

    catalog = _inventory_catalog(services)
    catalog.catalogWorkspace._set_selected_item_id(item_id)

    narrow_calls = []
    catalog.catalogWorkspace.refresh_selected_item_linked_documents = (
        lambda: narrow_calls.append("linked-docs") or None
    )
    full_calls = []
    catalog.catalogWorkspace.refresh = lambda: full_calls.append("full") or None

    document_service.add_link(
        document_id=document.id,
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=item_id,
    )

    assert narrow_calls == ["linked-docs"]
    assert full_calls == []


def test_catalog_unrelated_item_link_does_not_refresh_selected_item(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-CATALOG-OTHER-DOC"), title="Doc", storage_uri="C:/docs/l.pdf"
    )
    selected_item_id = _unique_code("P16D-CATALOG-SELECTED")
    other_item_id = _unique_code("P16D-CATALOG-OTHER")

    catalog = _inventory_catalog(services)
    catalog.catalogWorkspace._set_selected_item_id(selected_item_id)

    narrow_calls = []
    catalog.catalogWorkspace.refresh_selected_item_linked_documents = (
        lambda: narrow_calls.append("linked-docs") or None
    )

    document_service.add_link(
        document_id=document.id,
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=other_item_id,
    )

    assert narrow_calls == []


def test_catalog_does_not_full_refresh_on_link_via_document_links_path(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-CATALOG-NOFULL"), title="Doc", storage_uri="C:/docs/m.pdf"
    )
    item_id = _unique_code("P16D-CATALOG-NOFULL-ITEM")

    catalog = _inventory_catalog(services)
    catalog.catalogWorkspace._set_selected_item_id(item_id)
    full_calls = []
    catalog.catalogWorkspace.refresh = lambda: full_calls.append("full") or None

    document_service.add_link(
        document_id=document.id,
        module_code="inventory_procurement",
        entity_type="stock_item",
        entity_id=item_id,
    )

    assert full_calls == []


# ---------------------------------------------------------------------------
# UI: Admin
# ---------------------------------------------------------------------------


def test_admin_selected_document_link_refreshes_focus_narrowly(services):
    document_service = services["document_service"]
    document = document_service.create_document(
        document_code=_unique_code("P16D-ADMIN-DOC"), title="Doc", storage_uri="C:/docs/n.pdf"
    )

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documents
    catalog.adminWorkspace._document_controller._selected_document_id = document.id

    narrow_calls = []
    catalog.adminWorkspace._document_controller.refreshFocus = (
        lambda: narrow_calls.append("focus") or None
    )
    full_calls = []
    catalog.adminWorkspace.refresh = lambda: full_calls.append("full") or None

    document_service.add_link(
        document_id=document.id, module_code="qhse", entity_type="inspection", entity_id="admin-insp-1"
    )

    assert narrow_calls == ["focus"]
    assert full_calls == []


def test_admin_unselected_document_link_does_not_refresh_focus(services):
    document_service = services["document_service"]
    selected_document = document_service.create_document(
        document_code=_unique_code("P16D-ADMIN-SELECTED"), title="Selected Doc", storage_uri="C:/docs/o.pdf"
    )
    other_document = document_service.create_document(
        document_code=_unique_code("P16D-ADMIN-OTHER"), title="Other Doc", storage_uri="C:/docs/p.pdf"
    )

    catalog = _platform_catalog(services)
    catalog.adminWorkspace.documents
    catalog.adminWorkspace._document_controller._selected_document_id = selected_document.id

    narrow_calls = []
    catalog.adminWorkspace._document_controller.refreshFocus = (
        lambda: narrow_calls.append("focus") or None
    )

    document_service.add_link(
        document_id=other_document.id, module_code="qhse", entity_type="inspection", entity_id="admin-insp-2"
    )

    assert narrow_calls == []


# ---------------------------------------------------------------------------
# Reservations / Procurement disposition
# ---------------------------------------------------------------------------


def test_reservations_document_linking_has_no_ui_consumer():
    """P16A/P16D audit: reservation_service.list_reservation_documents/link_document/
    unlink_document exist at the application layer but are not exposed through any desktop API
    or UI controller/presenter -- there is nothing to wire a narrow refresh onto, and nothing
    would ever observe staleness. Proven by source absence, not asserted by assumption."""
    import glob

    hits = []
    for path in glob.glob("src/ui_qml/**/*.py", recursive=True) + glob.glob(
        "src/core/modules/inventory_procurement/api/desktop/**/*.py", recursive=True
    ):
        if "__pycache__" in path:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "list_reservation_documents" in source or "reservation_service.link_document" in source:
            hits.append(path)
    assert hits == [], hits


def test_procurement_document_linking_has_no_ui_consumer():
    import glob

    hits = []
    for path in glob.glob("src/ui_qml/**/*.py", recursive=True) + glob.glob(
        "src/core/modules/inventory_procurement/api/desktop/**/*.py", recursive=True
    ):
        if "__pycache__" in path:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "list_purchase_order_documents" in source or "purchasing_service.link_document" in source:
            hits.append(path)
    assert hits == [], hits


# ---------------------------------------------------------------------------
# DocumentLink trust boundary (caller-owned organization-scoped resolution)
# ---------------------------------------------------------------------------


def test_all_real_business_callers_resolve_entity_org_scoped_before_linking():
    """P16A found DocumentLink's entity_id is caller-trusted, not independently validated by the
    Document layer. P16D re-confirmed no clean generic cross-module resolver exists (building one
    would be exactly the forbidden generic entity resolver/service locator) and kept the
    invariant caller-owned. This proves every current REAL business-workflow caller resolves its
    entity through its own organization-scoped lookup before calling into
    DocumentIntegrationService -- Admin's manual add_link tool is a deliberately different,
    settings.manage-gated manual-entry path and is not held to this invariant."""
    import importlib
    import inspect

    from src.core.modules.inventory_procurement.application.inventory.reservation_service import (
        ReservationService,
    )
    from src.core.modules.inventory_procurement.application.procurement.purchasing_service import (
        PurchasingService,
    )
    from src.core.modules.project_management.application.collaboration.commands.collaboration_comments import (
        CollaborationCommentCommandMixin,
    )

    module_checks = [
        (
            "src.core.modules.inventory_procurement.application.catalog.item_document_service",
            ("link_document", "unlink_document"),
            "get_item(",
        ),
    ]
    for module_name, function_names, org_scoped_lookup in module_checks:
        module = importlib.import_module(module_name)
        for function_name in function_names:
            source = inspect.getsource(getattr(module, function_name))
            assert org_scoped_lookup in source, (
                f"{module_name}.{function_name} must resolve its entity via "
                f"{org_scoped_lookup} before linking a document"
            )

    class_checks = [
        (ReservationService, ("link_document", "unlink_document"), "self.get_reservation("),
        (PurchasingService, ("link_document", "unlink_document"), "self.get_purchase_order("),
        (CollaborationCommentCommandMixin, ("post_comment",), "self._require_task("),
    ]
    for owner_class, method_names, org_scoped_lookup in class_checks:
        for method_name in method_names:
            source = inspect.getsource(getattr(owner_class, method_name))
            assert org_scoped_lookup in source, (
                f"{owner_class.__name__}.{method_name} must resolve its entity via "
                f"{org_scoped_lookup} before linking a document"
            )


# ---------------------------------------------------------------------------
# documents_changed: fully deleted
# ---------------------------------------------------------------------------


def test_documents_changed_field_and_producers_and_consumers_are_fully_gone():
    assert not hasattr(domain_events, "documents_changed")

    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if "documents_changed" in source:
            hits.append(normalized)
    assert hits == [], hits


def test_legacy_signal_count_decreased_by_exactly_one():
    import dataclasses

    assert len(dataclasses.fields(domain_events)) == 29


# ---------------------------------------------------------------------------
# Architecture guards
# ---------------------------------------------------------------------------


def test_no_document_changed_or_document_updated_blanket_event():
    import glob
    import re

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        if re.search(r"\bDocumentChanged\b", source) or re.search(r"\bDocumentUpdated\b", source):
            hits.append(normalized)
    assert hits == [], hits


def test_no_new_signal_added_to_domain_events():
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(domain_events)}
    assert "document_links_changed" not in field_names
    assert "document_reference_changed" not in field_names


def test_no_generic_entity_resolver_or_service_locator_introduced():
    import inspect

    import src.core.platform.application.master_data.documents.document_commands as document_commands_module
    import src.core.platform.application.master_data.documents.document_integration_service as document_integration_service_module

    for module in (document_commands_module, document_integration_service_module):
        source = inspect.getsource(module)
        for forbidden in ("repository_for(", "resolve_adapter(", "container.get(", "entity_resolver"):
            assert forbidden not in source


def test_document_uow_retained_and_raw_session_commit_not_reintroduced():
    import inspect

    import src.core.platform.application.master_data.documents.document_commands as document_commands_module
    import src.core.platform.application.master_data.documents.document_integration_service as document_integration_service_module
    import src.core.platform.infrastructure.persistence.uow.document_unit_of_work as infra_module

    assert "class SqlAlchemyDocumentUnitOfWork(" in inspect.getsource(infra_module)
    for module in (document_commands_module, document_integration_service_module):
        source = inspect.getsource(module)
        assert "self._session.commit(" not in source
        assert "self._session.rollback(" not in source


def test_no_platform_to_business_module_concrete_infrastructure_import():
    import inspect

    import src.core.platform.infrastructure.persistence.uow.document_unit_of_work as infra_module

    source = inspect.getsource(infra_module)
    assert "core.modules" not in source
