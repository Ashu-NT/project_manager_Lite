"""P4-PRE Step 1 (ADR-005 Section 24, Round 8): `ProcurementApprovalParticipant` +
`build_procurement_approval_deps` -- proves the participant is genuinely session-parameterizable
(the Step-2 readiness criterion) and behaves identically to
`ProcurementApprovalMixin.apply_submitted_requisition_approval`/`_rejection` (kept unmodified --
the still-registered, long-lived `ProcurementService` calls them too).
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.modules.inventory_procurement.infrastructure.approval.procurement_apply_participant import (
    ProcurementApprovalParticipant,
)
from src.core.platform.contract.models.approval.contracts import ApprovalPostCommitEvent
from src.core.platform.domain.master_data.party import PartyType
from src.infra.composition.approval_apply_dependencies.procurement import (
    build_procurement_approval_deps,
)
from src.infra.persistence.orm.base import Base
from src.tests.ui_runtime_helpers import login_as


def _requisition_context(services):
    site = services["site_service"].create_site(
        site_code="APR",
        name="Approval Participant Site",
        currency_code="EUR",
    )
    item = services["inventory_item_service"].create_item(
        item_code="APR-PUMP-001",
        name="Approval Pump",
        status="ACTIVE",
        stock_uom="EA",
        is_purchase_allowed=True,
    )
    storeroom = services["inventory_service"].create_storeroom(
        storeroom_code="APR-MAIN",
        name="Approval Participant Main",
        site_id=site.id,
        status="ACTIVE",
    )
    supplier = services["party_service"].create_party(
        party_code="SUP-APR",
        party_name="Approval Pump Supply",
        party_type=PartyType.SUPPLIER,
    )
    return site, storeroom, item, supplier


def _submitted_requisition(services):
    auth = services["auth_service"]
    auth.register_user("apr-requester", "StrongPass123", role_names=["inventory_manager"])
    site, storeroom, item, supplier = _requisition_context(services)

    login_as(services, "apr-requester", "StrongPass123")

    procurement = services["inventory_procurement_service"]
    requisition = procurement.create_requisition(
        requesting_site_id=site.id,
        requesting_storeroom_id=storeroom.id,
        purpose="Restock critical spares",
        needed_by_date=date(2026, 4, 1),
    )
    procurement.add_requisition_line(
        requisition.id,
        stock_item_id=item.id,
        quantity_requested=5,
        suggested_supplier_party_id=supplier.id,
        estimated_unit_cost=120.0,
    )
    requisition = procurement.submit_requisition(requisition.id, note="Need this approved quickly")
    return requisition


def _pending_request(services, requisition):
    pending = services["approval_service"].list_pending()
    for request in pending:
        if request.id == requisition.approval_request_id:
            return request
    raise AssertionError("expected a pending approval request for the submitted requisition")


def _deps(services, session):
    return build_procurement_approval_deps(
        session,
        user_session=services["user_session"],
        tenant_context_service=services["tenant_context_service"],
    )


def test_participant_apply_approves_requisition_on_the_supplied_session(services, session):
    requisition = _submitted_requisition(services)
    request = _pending_request(services, requisition)
    deps = _deps(services, session)

    result = ProcurementApprovalParticipant().apply(request, deps)

    approved = deps.procurement_service._requisition_repo.get(requisition.id)
    lines = deps.procurement_service._requisition_line_repo.list_for_requisition(requisition.id)
    assert approved.status.value == "APPROVED"
    assert approved.approved_at is not None
    assert [line.status.value for line in lines] == ["OPEN"]
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("inventory_requisitions_changed", requisition.id),
    )


def test_participant_reject_rejects_requisition_on_the_supplied_session(services, session):
    requisition = _submitted_requisition(services)
    request = _pending_request(services, requisition)
    deps = _deps(services, session)

    result = ProcurementApprovalParticipant().reject(request, deps)

    rejected = deps.procurement_service._requisition_repo.get(requisition.id)
    lines = deps.procurement_service._requisition_line_repo.list_for_requisition(requisition.id)
    assert rejected.status.value == "REJECTED"
    assert [line.status.value for line in lines] == ["REJECTED"]
    assert result.post_commit_events == (
        ApprovalPostCommitEvent("inventory_requisitions_changed", requisition.id),
    )


def test_participant_never_calls_commit_or_rollback(services, session, monkeypatch):
    """The participant stages only -- the caller (today: ApprovalService on the shared Session;
    from Step 2 onward: its own PlatformUnitOfWork) owns transaction completion."""
    requisition = _submitted_requisition(services)
    request = _pending_request(services, requisition)
    deps = _deps(services, session)

    def _forbidden(*_args, **_kwargs):
        raise AssertionError("the participant must never commit or roll back its own Session")

    monkeypatch.setattr(type(session), "commit", _forbidden)
    monkeypatch.setattr(type(session), "rollback", _forbidden)

    ProcurementApprovalParticipant().apply(request, deps)


def test_dependencies_factory_binds_every_transaction_sensitive_field_to_the_supplied_session(
    tmp_path, services
):
    engine_a = create_engine(f"sqlite:///{tmp_path}/deps_a.db", future=True)
    engine_b = create_engine(f"sqlite:///{tmp_path}/deps_b.db", future=True)
    Base.metadata.create_all(engine_a)
    Base.metadata.create_all(engine_b)
    session_a = sessionmaker(bind=engine_a, future=True)()
    session_b = sessionmaker(bind=engine_b, future=True)()
    try:
        deps_a = _deps(services, session_a)
        deps_b = _deps(services, session_b)

        assert deps_a.procurement_service._session is session_a
        assert deps_b.procurement_service._session is session_b
        assert deps_a.procurement_service._requisition_repo.session is session_a
        assert deps_b.procurement_service._requisition_repo.session is session_b
        assert deps_a.procurement_service._requisition_line_repo.session is session_a
        assert deps_b.procurement_service._requisition_line_repo.session is session_b
        assert deps_a.procurement_service is not deps_b.procurement_service
        assert deps_a.procurement_service._approval_service is None, (
            "the apply path must never reach back into ApprovalService"
        )
        assert deps_b.procurement_service._approval_service is None
        assert deps_a.procurement_service._activity_service is None, (
            "record_activity must remain a silent no-op, matching current production behavior"
        )
    finally:
        session_a.close()
        session_b.close()


def test_dependencies_factory_never_opens_its_own_session(services, session):
    deps = _deps(services, session)
    assert deps.procurement_service._session is session, (
        "the factory must use the supplied Session, never a fresh one"
    )
