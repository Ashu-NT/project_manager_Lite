from __future__ import annotations

from datetime import date

import pytest

from src.core.platform.common.exceptions import ValidationError
from src.core.platform.domain.master_data.party import PartyType
from src.tests.ui_runtime_helpers import login_as


def _create_requisition_context(services):
    site = services["site_service"].create_site(
        site_code="REQ",
        name="Requisition Site",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="PUMP-001",
        name="Pump",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="REQ-MAIN",
        name="Requisition Main",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-REQ",
        party_name="Pump Supply",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def test_inventory_manager_can_submit_requisition_for_approval(services):
    auth = services["auth_service"]
    auth.register_user("inventory-requester", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _create_requisition_context(services)

    login_as(services, "inventory-requester", "StrongPass123")

    procurement = services["inventory_procurement_service"]
    approvals = services["approval_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Restock critical spares",
        needed_by_date=date(2026, 4, 1),
    )
    line = procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=120.0,
    )
    submitted = procurement.submit_requisition(requisition.id, note="Need this approved quickly")
    pending = approvals.list_pending()

    assert line.line_number == 1
    assert submitted.status.value == "SUBMITTED"
    assert submitted.approval_request_id is not None
    assert len(pending) == 1
    assert pending[0].request_type == "purchase_requisition.submit"
    assert pending[0].payload["requisition_id"] == requisition.id


def test_approver_can_approve_and_reject_inventory_requisitions(services):
    auth = services["auth_service"]
    auth.register_user("inventory-requester-2", "StrongPass123", role_names=["inventory_manager"])
    auth.register_user("inventory-approver", "StrongPass123", role_names=["approver"])
    site, storeroom, item, supplier = _create_requisition_context(services)
    procurement = services["inventory_procurement_service"]
    approvals = services["approval_service"]

    login_as(services, "inventory-requester-2", "StrongPass123")
    approved_req = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Approved requisition",
    )
    procurement.add_requisition_line(
        approved_req.id,
        stock_item_id=item.id,
        quantity_requested=3,
        suggested_supplier_party_id=supplier.id,
    )
    approved_req = procurement.submit_requisition(approved_req.id)
    approved_request_id = approved_req.approval_request_id

    rejected_req = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Rejected requisition",
    )
    procurement.add_requisition_line(
        rejected_req.id,
        stock_item_id=item.id,
        quantity_requested=2,
    )
    rejected_req = procurement.submit_requisition(rejected_req.id)
    rejected_request_id = rejected_req.approval_request_id

    login_as(services, "inventory-approver", "StrongPass123")

    approvals.approve_and_apply(approved_request_id, note="Approved")
    approvals.reject(rejected_request_id, note="Rejected")

    login_as(services, "inventory-requester-2", "StrongPass123")

    approved = procurement.get_requisition(approved_req.id)
    rejected = procurement.get_requisition(rejected_req.id)
    approved_lines = procurement.list_requisition_lines(approved.id)
    rejected_lines = procurement.list_requisition_lines(rejected.id)

    assert approved.status.value == "APPROVED"
    assert approved.approved_at is not None
    assert [line.status.value for line in approved_lines] == ["OPEN"]
    assert rejected.status.value == "REJECTED"
    assert [line.status.value for line in rejected_lines] == ["REJECTED"]


def test_submit_requisition_uses_a_fresh_uow_session_shared_by_the_approval_request(
    services, monkeypatch
):
    """Approval-P1: `submit_requisition` is converged onto `RequisitionSubmissionUnitOfWork` --
    a genuinely fresh Session per call, distinct from the shared legacy Session, with the
    requisition update and the Approval request sharing that one Session/transaction."""
    auth = services["auth_service"]
    auth.register_user("inventory-requester-uow", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _create_requisition_context(services)
    login_as(services, "inventory-requester-uow", "StrongPass123")

    procurement = services["inventory_procurement_service"]
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="UoW probe",
    )
    procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=1,
        suggested_supplier_party_id=supplier.id,
    )

    seen_uows = []
    original_create = type(procurement._requisition_submission_uow_factory).create

    def _spy_create(self, *, context):
        uow = original_create(self, context=context)
        seen_uows.append(uow)
        return uow

    monkeypatch.setattr(
        type(procurement._requisition_submission_uow_factory), "create", _spy_create
    )
    submitted = procurement.submit_requisition(requisition.id)

    assert len(seen_uows) == 1
    uow = seen_uows[0]
    assert uow._session is not procurement._session
    assert uow.requisitions.session is uow._session
    assert uow.approvals.session is uow._session
    assert uow._enterprise_audit_service._session is uow._session
    assert submitted.status.value == "SUBMITTED"


def test_submit_requisition_audit_failure_rolls_back_requisition_and_approval_request_together(
    services, monkeypatch
):
    from src.core.platform.application.history.audit.enterprise_audit_service import (
        EnterpriseAuditService,
    )

    auth = services["auth_service"]
    auth.register_user("inventory-requester-auditfail", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _create_requisition_context(services)
    login_as(services, "inventory-requester-auditfail", "StrongPass123")

    procurement = services["inventory_procurement_service"]
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Audit-failure probe",
    )
    procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=1,
        suggested_supplier_party_id=supplier.id,
    )

    def _fail_record(self, **kwargs):
        raise RuntimeError("simulated approval audit failure")

    monkeypatch.setattr(EnterpriseAuditService, "record", _fail_record)

    with pytest.raises(RuntimeError, match="simulated approval audit failure"):
        procurement.submit_requisition(requisition.id)

    monkeypatch.undo()
    reloaded = procurement.get_requisition(requisition.id)
    assert reloaded.status.value == "DRAFT"
    assert reloaded.approval_request_id is None
    lines = procurement.list_requisition_lines(requisition.id)
    assert all(line.status.value == "DRAFT" for line in lines)
    assert services["approval_service"].list_pending() == []


def test_requisition_service_validates_draft_and_line_rules(services):
    site, storeroom, item, _supplier = _create_requisition_context(services)
    procurement = services["inventory_procurement_service"]

    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
    )

    with pytest.raises(ValidationError, match="at least one line"):
        procurement.submit_requisition(requisition.id)
    with pytest.raises(ValidationError, match="stock UOM"):
        procurement.add_requisition_line(
            requisition.id,
            stock_item_id=item.id,
            quantity_requested=1,
            uom="BOX",
        )


def test_requisition_service_can_update_and_cancel_draft_requisition(services):
    auth = services["auth_service"]
    auth.register_user("inventory-requester-edit", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _create_requisition_context(services)
    alternate_site = services["site_service"].create_site(
        site_code="REQ-ALT",
        name="Alternate Requisition Site",
        currency_code="EUR",
    )
    alternate_storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="REQ-ALT-MAIN",
        name="Alternate Requisition Stores",
        site_id=alternate_site.id,
        status="ACTIVE",
    )

    login_as(services, "inventory-requester-edit", "StrongPass123")

    procurement = services["inventory_procurement_service"]
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Initial demand",
    )
    procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=2,
        suggested_supplier_party_id=supplier.id,
    )

    updated = procurement.update_requisition(
        requisition.id,
        requesting_site_id=alternate_site.id,
        requesting_storeroom_id=alternate_storeroom.id,
        purpose="Updated demand",
        needed_by_date=date(2026, 5, 2),
        priority="URGENT",
        notes="Replanned before approval",
        expected_version=requisition.version,
    )
    cancelled = procurement.cancel_requisition(updated.id, expected_version=updated.version)
    lines = procurement.list_requisition_lines(updated.id)

    assert updated.requesting_site_id == alternate_site.id
    assert updated.requesting_storeroom_id == alternate_storeroom.id
    assert updated.purpose == "Updated demand"
    assert updated.needed_by_date == date(2026, 5, 2)
    assert updated.priority == "URGENT"
    assert cancelled.status.value == "CANCELLED"
    assert cancelled.cancelled_at is not None
    assert [line.status.value for line in lines] == ["CANCELLED"]

