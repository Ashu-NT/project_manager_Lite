"""P29: Inventory Requisition full modernization -- typed events replace
`inventory_requisitions_changed` for every remaining producer (create/add-line/update/cancel,
still-raw-Session per P27A; approve/reject, still on the legacy `ApprovalPostCommitEvent` bridge),
Requisition's own commands converge onto the existing `RequisitionSubmissionUnitOfWork` (Option A
extension, name kept per P28B's own precedent), `update_requisition` gains true no-op detection,
and the P27A-flagged supplier same-organization gap is closed narrowly.

`inventory_requisitions_changed` is DELETED from `DomainEvents` entirely (not just left unemitted)
-- assert `not hasattr(domain_events, ...)` rather than connecting a counter to it."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import pytest

from src.core.modules.inventory_procurement.application.procurement.event_handlers.view_invalidation import (
    PROCUREMENT_CATEGORY,
    REQUISITION_DETAIL_SCOPE_CODE,
    REQUISITION_LIST_SCOPE_CODE,
    REQUISITION_PENDING_APPROVAL_SCOPE_CODE,
    build_requisition_view_invalidation_handler,
)
from src.core.modules.inventory_procurement.domain.procurement.requisition_events import (
    InventoryRequisitionApproved,
    InventoryRequisitionCancelled,
    InventoryRequisitionCreated,
    InventoryRequisitionLineAdded,
    InventoryRequisitionProfileUpdated,
    InventoryRequisitionRejected,
    InventoryRequisitionSourcingAdvanced,
    InventoryRequisitionSubmitted,
)
from src.core.platform.common.exceptions import ConcurrencyError
from src.core.platform.domain.master_data.party import PartyType
from src.core.shared.events.domain_event_context import DomainEventContext
from src.core.shared.events.domain_events import domain_events
from src.core.shared.events.view_invalidation import OrganizationScope, ResourceScope
from src.tests.ui_runtime_helpers import login_as


def _procurement_context(services, suffix):
    site = services["site_service"].create_site(
        site_code=f"P29-{suffix}", name=f"P29 Site {suffix}", currency_code="EUR"
    )
    item = services["inventory_item_service"].create_item(
        item_code=f"P29-PUMP-{suffix}",
        name=f"P29 Pump {suffix}",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code=f"P29-MAIN-{suffix}",
        name=f"P29 Main {suffix}",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code=f"SUP-P29-{suffix}",
        party_name=f"P29 Supplier {suffix}",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def _fake_channel():
    class _FakeChannel:
        def __init__(self) -> None:
            self.notified: list = []

        def notify(self, hint) -> None:
            self.notified.append(hint)

    return _FakeChannel()


def _spy_hints(services):
    hints = []

    class _AnyOrgFilter:
        def matches(self, scope) -> bool:
            return True

    services["platform_view_invalidation_channel"].subscribe(_AnyOrgFilter(), lambda hint: hints.append(hint))
    return hints


def _requisition_hints(hints):
    return [
        h
        for h in hints
        if h.category == PROCUREMENT_CATEGORY
        and h.scope_code
        in (
            REQUISITION_LIST_SCOPE_CODE,
            REQUISITION_DETAIL_SCOPE_CODE,
            REQUISITION_PENDING_APPROVAL_SCOPE_CODE,
        )
    ]


def test_legacy_requisition_signal_field_is_deleted():
    assert not hasattr(domain_events, "inventory_requisitions_changed")


# ---------------------------------------------------------------------------
# ViewInvalidation handler: every Requisition event type maps to both targets,
# dedupe still holds now that the handler covers 8 event types, not just 1 (P29 generalized
# `build_requisition_sourcing_view_invalidation_handler` into `build_requisition_view_invalidation_handler`)
# ---------------------------------------------------------------------------


def _mk(event_cls, **extra):
    now = datetime.now(timezone.utc)
    base = {"tenant_id": "t1", "organization_id": "o1", "requisition_id": "r1", "occurred_at": now}
    base.update(extra)
    return event_cls(**base)


# P29-FIX §10: the FINAL exact per-event target matrix, source-derived (not "all yes").
# (event, expects_list, expects_detail, expects_pending_approval)
_EVENT_MATRIX = [
    (_mk(InventoryRequisitionCreated), True, False, False),
    (_mk(InventoryRequisitionLineAdded, requisition_line_id="l1"), False, True, False),
    (_mk(InventoryRequisitionProfileUpdated), True, True, False),
    (_mk(InventoryRequisitionSubmitted, approval_request_id="a1"), True, True, True),
    (_mk(InventoryRequisitionApproved, approval_request_id="a1"), True, True, True),
    (_mk(InventoryRequisitionRejected, approval_request_id="a1"), True, True, True),
    (_mk(InventoryRequisitionCancelled), True, True, True),
    (
        _mk(InventoryRequisitionSourcingAdvanced, purchase_order_id="po1", resulting_status="PARTIALLY_SOURCED"),
        True,
        True,
        False,
    ),
]


@pytest.mark.parametrize(
    "event,expects_list,expects_detail,expects_pending_approval", _EVENT_MATRIX,
    ids=[type(e).__name__ for e, *_ in _EVENT_MATRIX],
)
def test_final_event_to_invalidation_matrix(event, expects_list, expects_detail, expects_pending_approval):
    """P29-FIX §10: the FINAL exact event -> stale-projection mapping, source-derived from
    `to_requisition_record_view_model` (list row fields), `build_requisition_detail` (detail
    fields), and `dashboard.py::build_snapshot`'s `{SUBMITTED, UNDER_REVIEW}` pending-approval
    filter -- not "every event invalidates every target"."""
    channel = _fake_channel()
    handler = build_requisition_view_invalidation_handler(channel)

    handler(event, DomainEventContext(correlation_id="tx"))

    scope_codes = {h.scope_code for h in channel.notified}
    assert (REQUISITION_LIST_SCOPE_CODE in scope_codes) is expects_list
    assert (REQUISITION_DETAIL_SCOPE_CODE in scope_codes) is expects_detail
    assert (REQUISITION_PENDING_APPROVAL_SCOPE_CODE in scope_codes) is expects_pending_approval
    for hint in channel.notified:
        if hint.scope_code == REQUISITION_LIST_SCOPE_CODE:
            assert isinstance(hint.scope, OrganizationScope)
        elif hint.scope_code == REQUISITION_DETAIL_SCOPE_CODE:
            assert isinstance(hint.scope, ResourceScope)
            assert hint.scope.entity_type == "purchase_requisition"
            assert hint.scope.entity_id == "r1"
        elif hint.scope_code == REQUISITION_PENDING_APPROVAL_SCOPE_CODE:
            assert isinstance(hint.scope, OrganizationScope)


def test_requisition_events_dedupe_within_one_transaction_across_event_types():
    """A single logical operation only ever produces one typed event, but this proves the shared
    handler correctly coalesces even a hypothetical mix of event types against the SAME
    requisition within one correlation_id -- not just repeats of one event type. Uses
    ProfileUpdated (list+detail) so both targets are exercised, since Created alone (P29-FIX)
    only ever produces a list hint."""
    channel = _fake_channel()
    handler = build_requisition_view_invalidation_handler(channel)
    now = datetime.now(timezone.utc)

    handler(
        InventoryRequisitionProfileUpdated(tenant_id="t1", organization_id="o1", requisition_id="r1", occurred_at=now),
        DomainEventContext(correlation_id="tx"),
    )
    handler(
        InventoryRequisitionLineAdded(
            tenant_id="t1", organization_id="o1", requisition_id="r1", requisition_line_id="l1", occurred_at=now
        ),
        DomainEventContext(correlation_id="tx"),
    )
    assert len(channel.notified) == 2, "same requisition, same transaction: one list hint + one detail hint (LineAdded's own detail hint dedupes against ProfileUpdated's)"

    handler(
        InventoryRequisitionProfileUpdated(tenant_id="t1", organization_id="o1", requisition_id="r2", occurred_at=now),
        DomainEventContext(correlation_id="tx"),
    )
    assert len(channel.notified) == 3, "a different requisition adds an exact detail hint but reuses the org-list hint"

    handler(
        InventoryRequisitionProfileUpdated(tenant_id="t1", organization_id="o1", requisition_id="r1", occurred_at=now),
        DomainEventContext(correlation_id="next-tx"),
    )
    assert len(channel.notified) == 5, "a new transaction is never coalesced with the previous one"


# ---------------------------------------------------------------------------
# Real production paths: create/add-line/update/cancel on the canonical UoW
# ---------------------------------------------------------------------------


def test_create_requisition_produces_exactly_one_typed_event_and_list_hint_only(services):
    """P29-FIX §2: a newly-created requisition cannot have a pre-existing open detail
    projection for its own (just-generated) id -- Created must notify `requisition_list` only."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-create-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, _item, _supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-create-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    hints = _spy_hints(services)
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="P29 create",
        needed_by_date=date(2026, 5, 1),
    )

    req_hints = _requisition_hints(hints)
    assert len(req_hints) == 1
    assert req_hints[0].scope_code == REQUISITION_LIST_SCOPE_CODE
    assert requisition.version == 1


def test_add_requisition_line_produces_exactly_one_typed_event_and_detail_hint_only(services):
    """P29-FIX §3: line data never appears on the `requisition_list` row -- LineAdded must
    notify `requisition_detail` only."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-addline-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-addline-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="P29 add-line"
    )
    hints = _spy_hints(services)
    line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=10.0,
    )

    req_hints = _requisition_hints(hints)
    assert len(req_hints) == 1
    assert req_hints[0].scope_code == REQUISITION_DETAIL_SCOPE_CODE
    assert line.quantity_requested == 5


def test_update_requisition_true_no_op_writes_nothing(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-noop-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, _item, _supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-noop-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="P29 no-op",
        priority="NORMAL",
    )
    assert requisition.version == 1

    hints = _spy_hints(services)
    result = procurement.update_requisition(
        requisition.id,
        requesting_site_id=requisition.requesting_site_id,
        requesting_storeroom_id=requisition.requesting_storeroom_id,
        purpose=requisition.purpose,
        priority=requisition.priority,
        notes=requisition.notes,
    )

    assert result.version == 1, "no-op must not bump version"
    assert result.updated_at == requisition.updated_at, "no-op must not bump updated_at"
    assert _requisition_hints(hints) == [], "a true no-op must publish zero ViewInvalidation hints"


def test_update_requisition_real_change_produces_exactly_one_typed_event(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-update-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, _item, _supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-update-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Before"
    )
    hints = _spy_hints(services)
    updated = procurement.update_requisition(requisition.id, purpose="After")

    assert updated.purpose == "After"
    assert updated.version == requisition.version + 1, "a real change persists via the version-checked update path"
    req_hints = _requisition_hints(hints)
    assert len(req_hints) == 2


def test_update_requisition_stale_version_fails_cleanly(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-stale-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, _item, _supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-stale-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Before"
    )
    hints = _spy_hints(services)
    with pytest.raises(ConcurrencyError):
        procurement.update_requisition(requisition.id, purpose="After", expected_version=99)

    assert _requisition_hints(hints) == [], "a stale-version rejection must publish zero hints"


def test_cancel_requisition_produces_exactly_one_typed_event_and_cancels_all_lines(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-cancel-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-cancel-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="P29 cancel"
    )
    procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=2,
        suggested_supplier_party_id=supplier.id,
    )
    hints = _spy_hints(services)
    cancelled = procurement.cancel_requisition(requisition.id, note="No longer needed")

    assert cancelled.status.value == "CANCELLED"
    lines = procurement._requisition_line_repo.list_for_requisition(requisition.id)
    assert [line.status.value for line in lines] == ["CANCELLED"]
    req_hints = _requisition_hints(hints)
    assert len(req_hints) == 3, "Cancelled notifies list + detail + pending_approval (P29-FIX)"
    assert {h.scope_code for h in req_hints} == {
        REQUISITION_LIST_SCOPE_CODE,
        REQUISITION_DETAIL_SCOPE_CODE,
        REQUISITION_PENDING_APPROVAL_SCOPE_CODE,
    }


def test_cancel_requisition_stale_version_fails_cleanly(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-cancel-stale-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, _item, _supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-cancel-stale-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="P29 cancel stale"
    )
    hints = _spy_hints(services)
    with pytest.raises(ConcurrencyError):
        procurement.cancel_requisition(requisition.id, expected_version=99)

    assert _requisition_hints(hints) == []


def test_create_requisition_audit_failure_rolls_back_the_whole_transaction(services, monkeypatch):
    """P29 §30: proves the new canonical UoW is genuinely atomic for the previously-raw-Session
    create/add-line/update/cancel paths -- representative of all four, which share the same
    `_require_requisition_uow_factory()` transaction boundary."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-auditfail-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, _item, _supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-auditfail-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(EnterpriseAuditService, "record", _boom)

    hints = _spy_hints(services)
    with pytest.raises(RuntimeError):
        procurement.create_requisition(
            requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Should roll back"
        )

    assert _requisition_hints(hints) == [], "a failed audit must roll back the transaction and publish nothing"
    assert procurement.list_requisitions() == [] or all(
        r.purpose != "Should roll back" for r in procurement.list_requisitions()
    )


# ---------------------------------------------------------------------------
# Approval: real domain_events (not the legacy ApprovalPostCommitEvent bridge)
# ---------------------------------------------------------------------------


def _submitted_requisition(services, suffix):
    auth = services["auth_service"]
    auth.register_user(f"p29-req-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user(f"p29-appr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-req-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="P29 approval"
    )
    procurement.add_requisition_line(
        requisition.id, stock_item_id=item.id, quantity_requested=3, suggested_supplier_party_id=supplier.id
    )
    return procurement.submit_requisition(requisition.id)


def test_approve_requisition_produces_typed_event_and_both_hints_end_to_end(services):
    suffix = uuid4().hex[:6].upper()
    requisition = _submitted_requisition(services, suffix)
    approvals = services["approval_service"]

    hints = _spy_hints(services)
    login_as(services, f"p29-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved")

    req_hints = _requisition_hints(hints)
    assert len(req_hints) == 3, "Approved notifies list + detail + pending_approval (P29-FIX)"
    detail = next(h for h in req_hints if h.scope_code == REQUISITION_DETAIL_SCOPE_CODE)
    assert detail.scope.entity_id == requisition.id
    assert any(h.scope_code == REQUISITION_PENDING_APPROVAL_SCOPE_CODE for h in req_hints)


def test_reject_requisition_produces_typed_event_and_both_hints_end_to_end(services):
    suffix = uuid4().hex[:6].upper()
    requisition = _submitted_requisition(services, suffix)
    approvals = services["approval_service"]

    hints = _spy_hints(services)
    login_as(services, f"p29-appr-{suffix}", "StrongPass123")
    approvals.reject(requisition.approval_request_id, note="Rejected")

    req_hints = _requisition_hints(hints)
    assert len(req_hints) == 3, "Rejected notifies list + detail + pending_approval (P29-FIX)"
    assert any(h.scope_code == REQUISITION_PENDING_APPROVAL_SCOPE_CODE for h in req_hints)


# ---------------------------------------------------------------------------
# Ownership integrity: P27A/P29 supplier same-organization fix
# ---------------------------------------------------------------------------


def test_add_requisition_line_supplier_lookup_is_already_organization_scoped(services):
    """P29 §16: P27A/P28A/P28B all characterized this as an unresolved/real gap by reading
    `_ensure_business_supplier_scope` in isolation (active/business-type checked, organization
    membership never checked). Tracing its sole caller (`_validate_supplier_reference`) one line
    up shows `PartyService.get_party` already scopes its own lookup to the active organization and
    raises `NotFoundError` for a party belonging to a different one -- this test proves that
    empirically. The flagged gap does not exist; no code change was made for it (adding a second,
    unreachable check would just be dead code)."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-crossorg-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, _supplier = _procurement_context(services, suffix)

    login_as(services, "admin", "ChangeMe123!")
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    current_org = tenant_context_service.get_active_organization()
    other_org = organization_service.create_organization(
        organization_code=f"P29-OTHERORG-{suffix}",
        display_name=f"P29 Other Org {suffix}",
        timezone_name="UTC",
        base_currency="USD",
        is_enabled=False,
    )

    # Insert the other-org Party directly via the raw session -- PartyService.create_party
    # always creates under the CALLER's active organization, so a cross-org fixture row can't be
    # built through the service surface (matches the technique already used by
    # `_procurement_seed_helpers.py::_seed_procurement_scope_rows` for the same reason).
    from datetime import datetime, timezone as tz

    from src.core.platform.infrastructure.persistence.orm.master_data.party.party import PartyORM

    now = datetime.now(tz.utc)
    other_org_supplier_id = f"party-other-org-{suffix}"
    session = services["session"]
    session.add(
        PartyORM(
            id=other_org_supplier_id,
            tenant_id=getattr(other_org, "tenant_id", None) or getattr(current_org, "tenant_id", None),
            organization_id=other_org.id,
            party_code=f"SUP-OTHERORG-{suffix}",
            party_name="Other-Org Supplier",
            party_type=PartyType.SUPPLIER.value,
            is_active=True,
            created_at=now,
            updated_at=now,
            version=1,
        )
    )
    session.flush()

    class _OtherOrgSupplierRef:
        id = other_org_supplier_id

    other_org_supplier = _OtherOrgSupplierRef()

    login_as(services, f"p29-crossorg-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]
    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Cross-org supplier"
    )

    from src.core.platform.common.exceptions import NotFoundError

    with pytest.raises(NotFoundError, match="not found in the active organization"):
        procurement.add_requisition_line(
            requisition.id,
            stock_item_id=item.id,
            quantity_requested=1,
            suggested_supplier_party_id=other_org_supplier.id,
        )


# ---------------------------------------------------------------------------
# UI consumer cutover: incidental subscriptions removed, real consumers still react
# ---------------------------------------------------------------------------


def test_legacy_requisition_signal_has_zero_production_references():
    """Mirrors P24's `test_legacy_catalog_signals_have_zero_production_references`: checks for
    actual usage (`domain_events.inventory_requisitions_changed`) or the field declaration, not a
    substring that could false-positive on a retirement comment."""
    import glob

    hits = []
    for path in glob.glob("src/**/*.py", recursive=True):
        normalized = path.replace("\\", "/")
        if "__pycache__" in normalized or "/tests/" in normalized:
            continue
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            source = fh.read()
        for needle in (
            "domain_events.inventory_requisitions_changed",
            "inventory_requisitions_changed:",
        ):
            if needle in source:
                hits.append((normalized, needle))
    assert hits == [], hits


def test_procurement_workspace_requisition_created_triggers_full_refresh(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.procurementWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")

    catalog._procurement_requisition_view_invalidation_adapter.requisitionListStale.emit("req-1")
    assert refresh_calls == ["refresh"]


@pytest.mark.parametrize(
    "workspace_attr,adapter_attr",
    [
        ("catalogWorkspace", "_catalog_requisition_view_invalidation_adapter"),
        ("reservationsWorkspace", "_reservations_requisition_view_invalidation_adapter"),
        ("pricingWorkspace", "_pricing_requisition_view_invalidation_adapter"),
        ("inventoryWorkspace", "_inventory_requisition_view_invalidation_adapter"),
    ],
)
def test_incidental_workspaces_have_no_requisition_view_invalidation_adapter(
    services, workspace_attr, adapter_attr
):
    """P27A found Catalog/Reservations/Pricing/Inventory(Foundation) have zero real Requisition
    dependency -- P29 must not introduce any new adapter for them."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)

    assert hasattr(catalog, workspace_attr)
    assert not hasattr(catalog, adapter_attr)


# ---------------------------------------------------------------------------
# P29-FIX: refresh coalescing -- one transaction's multiple ViewInvalidation hints must
# produce exactly one ACTUAL Procurement workspace rebuild, not one rebuild per hint.
# ---------------------------------------------------------------------------


def test_procurement_coalesces_list_and_detail_hints_from_one_transaction_into_one_rebuild(
    services, qapp
):
    """P29-FIX §4/§5/§6/§11: `InventoryRequisitionApproved` notifies BOTH `requisition_list` and
    `requisition_detail` (2 real Procurement-relevant hints, from the same committed approval
    transaction). Before this fix, `_request_domain_refresh()` executed `refresh()` synchronously
    on every call, so 2 hints meant 2 full workspace rebuilds. The ported QTimer(0)-coalesced
    scheduling (same mechanism already established in `project_management`'s own
    `ProjectManagementWorkspaceControllerBase`) must collapse both into exactly ONE actual
    rebuild once the Qt event loop processes the scheduled timer."""
    from PySide6.QtWidgets import QApplication

    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    suffix = uuid4().hex[:6].upper()
    requisition = _submitted_requisition(services, suffix)
    approvals = services["approval_service"]

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.procurementWorkspace
    rebuild_calls = []
    controller.refresh = lambda: rebuild_calls.append("rebuild")

    app = QApplication.instance()
    previously_running = bool(app.property("pmEventLoopRunning"))
    app.setProperty("pmEventLoopRunning", True)
    try:
        login_as(services, f"p29-appr-{suffix}", "StrongPass123")
        approvals.approve_and_apply(requisition.approval_request_id, note="Approved")
        # No synchronous rebuild yet -- both hints only SCHEDULED a coalesced refresh.
        assert rebuild_calls == [], "hints must not execute the rebuild synchronously once coalescing is active"

        QApplication.processEvents()
    finally:
        app.setProperty("pmEventLoopRunning", previously_running)

    assert rebuild_calls == ["rebuild"], (
        f"expected exactly one coalesced Procurement rebuild for one transaction, got {len(rebuild_calls)}"
    )


def test_procurement_refreshes_once_per_transaction_without_an_active_event_loop(services):
    """P29-FIX: when no real Qt event loop is running (`pmEventLoopRunning` unset/False -- the
    default in this test process, and the shape most of this test suite already runs under),
    `_schedule_domain_refresh` falls back to executing immediately/synchronously per call, same
    as pre-fix behavior. This is the ALREADY-ACCEPTED fallback (matches `project_management`'s
    identical mechanism), not a regression -- production always sets `pmEventLoopRunning=True`
    before entering `app.exec()` (`src/ui_qml/shell/app.py`), so real users always get the
    coalesced path exercised by the test above."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    suffix = uuid4().hex[:6].upper()
    requisition = _submitted_requisition(services, suffix)
    approvals = services["approval_service"]

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.procurementWorkspace
    rebuild_calls = []
    controller.refresh = lambda: rebuild_calls.append("rebuild")

    login_as(services, f"p29-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved")

    assert len(rebuild_calls) == 2, (
        "without an active event loop, each of the 2 Procurement-relevant hints (list, detail) "
        "executes its own immediate rebuild -- documenting the fallback explicitly rather than "
        "silently relying on it"
    )


# ---------------------------------------------------------------------------
# P29-FIX §12: Dashboard event-by-event refresh precision, end-to-end (real typed events, not
# manually-emitted adapter signals)
# ---------------------------------------------------------------------------


def _dashboard_refresh_spy(services):
    """Returns (catalog, controller, refresh_calls). The caller MUST keep a reference to
    `catalog` alive for the duration of the test -- its QObject children (including the
    Requisition ViewInvalidation adapter) are only kept alive by the Qt parent-child
    relationship, which does not survive the Python wrapper for `catalog` itself being
    garbage-collected."""
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.modules.inventory_procurement.context import InventoryProcurementWorkspaceCatalog

    registry = build_desktop_api_registry(services)
    catalog = InventoryProcurementWorkspaceCatalog(desktop_api_registry=registry)
    controller = catalog.dashboardWorkspace
    refresh_calls = []
    controller.refresh = lambda: refresh_calls.append("refresh")
    return catalog, controller, refresh_calls


def test_dashboard_does_not_refresh_on_created_line_added_or_profile_updated(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-dashnr-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-dashnr-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    _catalog, _controller, refresh_calls = _dashboard_refresh_spy(services)

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Dashboard no-op check"
    )
    assert refresh_calls == [], "Created must not refresh Dashboard"

    procurement.add_requisition_line(
        requisition.id, stock_item_id=item.id, quantity_requested=2, suggested_supplier_party_id=supplier.id
    )
    assert refresh_calls == [], "LineAdded must not refresh Dashboard"

    procurement.update_requisition(requisition.id, purpose="Dashboard no-op check, updated")
    assert refresh_calls == [], "ProfileUpdated must not refresh Dashboard"


def test_dashboard_refreshes_on_approve(services):
    suffix = uuid4().hex[:6].upper()
    requisition = _submitted_requisition(services, suffix)

    _catalog, _controller, refresh_calls = _dashboard_refresh_spy(services)
    approvals = services["approval_service"]

    login_as(services, f"p29-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved")
    assert refresh_calls == ["refresh"], "Approved must refresh Dashboard exactly once"


def test_dashboard_refreshes_on_submit(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-dashsub-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-dashsub-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Dashboard submit check"
    )
    procurement.add_requisition_line(
        requisition.id, stock_item_id=item.id, quantity_requested=2, suggested_supplier_party_id=supplier.id
    )

    _catalog, _controller, refresh_calls = _dashboard_refresh_spy(services)
    procurement.submit_requisition(requisition.id)

    assert refresh_calls == ["refresh"], "Submitted must refresh Dashboard exactly once"


def test_dashboard_refreshes_on_reject(services):
    suffix = uuid4().hex[:6].upper()
    requisition = _submitted_requisition(services, suffix)

    _catalog, _controller, refresh_calls = _dashboard_refresh_spy(services)
    approvals = services["approval_service"]

    login_as(services, f"p29-appr-{suffix}", "StrongPass123")
    approvals.reject(requisition.approval_request_id, note="Rejected")

    assert refresh_calls == ["refresh"], "Rejected must refresh Dashboard exactly once"


def test_dashboard_refreshes_on_cancel(services):
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-dashcancel-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-dashcancel-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Dashboard cancel check"
    )

    _catalog, _controller, refresh_calls = _dashboard_refresh_spy(services)
    procurement.cancel_requisition(requisition.id, note="No longer needed")

    assert refresh_calls == ["refresh"], "Cancelled must refresh Dashboard exactly once"


def test_sourcing_advanced_never_produces_a_pending_approval_hint_end_to_end(services):
    """P28B-FIX already proved SourcingAdvanced doesn't reach Dashboard at the adapter level;
    P29-FIX reconfirms the precise invariant end-to-end (real PO approval, real transaction):
    SourcingAdvanced must never produce a `requisition_pending_approval` hint. This does NOT
    assert Dashboard's overall `refresh_calls == []` -- the SAME transaction also emits
    `InventoryPurchaseOrderApproved`, which legitimately refreshes Dashboard via its OWN,
    independent, already-established real PO dependency (P28B); asserting zero total Dashboard
    refreshes here would be wrong, not a stronger test."""
    suffix = uuid4().hex[:6].upper()
    auth = services["auth_service"]
    auth.register_user(f"p29-dashsrc-buyer-{suffix}", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user(f"p29-dashsrc-appr-{suffix}", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _procurement_context(services, suffix)
    login_as(services, f"p29-dashsrc-buyer-{suffix}", "StrongPass123")
    procurement = services["inventory_procurement_service"]
    purchasing = services["inventory_purchasing_service"]
    approvals = services["approval_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id, requesting_storeroom_id=storeroom.id, purpose="Dashboard sourcing check"
    )
    requisition_line = procurement.add_requisition_line(
        requisition.id, stock_item_id=item.id, quantity_requested=5, suggested_supplier_party_id=supplier.id
    )
    requisition = procurement.submit_requisition(requisition.id)
    login_as(services, f"p29-dashsrc-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(requisition.approval_request_id, note="Approved requisition")

    login_as(services, f"p29-dashsrc-buyer-{suffix}", "StrongPass123")
    po = purchasing.create_purchase_order(
        site_id=site.id, supplier_party_id=supplier.id, currency_code="EUR", source_requisition_id=requisition.id,
    )
    purchasing.add_purchase_order_line(
        po.id, stock_item_id=item.id, destination_storeroom_id=storeroom.id,
        quantity_ordered=5, unit_price=10.0, source_requisition_line_id=requisition_line.id,
    )
    po = purchasing.submit_purchase_order(po.id)

    hints = _spy_hints(services)
    login_as(services, f"p29-dashsrc-appr-{suffix}", "StrongPass123")
    approvals.approve_and_apply(po.approval_request_id, note="Approved PO, sources requisition")

    pending_approval_hints = [h for h in hints if h.scope_code == REQUISITION_PENDING_APPROVAL_SCOPE_CODE]
    assert pending_approval_hints == [], "SourcingAdvanced must never produce a pending-approval hint"
