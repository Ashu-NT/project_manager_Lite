"""P4 Step 2 (ADR-005 Section 24, Round 7/8): `SqlAlchemyPlatformUnitOfWork`/
`SqlAlchemyPlatformUnitOfWorkFactory` -- proven directly, before `ApprovalService` is cut over
onto them.
"""

from __future__ import annotations

import datetime as _dt

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.platform.domain.approval import ApprovalRequest
from src.core.platform.infrastructure.persistence.unit_of_work import (
    SqlAlchemyPlatformUnitOfWork,
    SqlAlchemyPlatformUnitOfWorkFactory,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.orm.base import Base


class _FakeTenantContextService:
    def __init__(self, tenant_id="tenant-a", organization_id="org-a"):
        self._tenant_id = tenant_id
        self._organization_id = organization_id

    def require_active_scope_ids(self, *, operation_label):
        from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds

        return ActiveScopeIds(tenant_id=self._tenant_id, organization_id=self._organization_id)

    def require_active_organization_id(self, *, operation_label):
        return self._organization_id

    def get_active_tenant_id(self):
        return self._tenant_id


def _factory(tmp_path, name="platform_uow.db"):
    engine = create_engine(f"sqlite:///{tmp_path}/{name}", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    return SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=session_factory,
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=_FakeTenantContextService(),
        user_session=None,
    )


def _context(correlation_id="corr-1"):
    return DomainEventContext(correlation_id=correlation_id)


def test_create_returns_a_platform_unit_of_work_with_approvals_and_audit_bound_to_a_fresh_session(
    tmp_path,
):
    factory = _factory(tmp_path)
    uow = factory.create(context=_context())
    assert isinstance(uow, SqlAlchemyPlatformUnitOfWork)
    assert uow.approvals.session is uow._session
    assert uow._enterprise_audit_service._session is uow._session
    uow._session.close()


def test_two_create_calls_open_genuinely_independent_sessions(tmp_path):
    factory = _factory(tmp_path)
    uow1 = factory.create(context=_context("c1"))
    uow2 = factory.create(context=_context("c2"))
    assert uow1._session is not uow2._session
    assert uow1.approvals is not uow2.approvals
    assert uow1.approvals.session is not uow2.approvals.session
    uow1._session.close()
    uow2._session.close()


def test_approval_request_commits_via_the_platform_uow(tmp_path):
    factory = _factory(tmp_path)
    request = ApprovalRequest.create(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id="budget-1",
        tenant_id="tenant-a",
        project_id="project-1",
        organization_id="org-a",
        payload={"budget_id": "budget-1"},
        requested_by_user_id="user-1",
        requested_by_username="requester",
    )
    with factory.create(context=_context()) as uow:
        uow.approvals.add(request)
        uow.commit()

    with factory.create(context=_context("verify")) as verify_uow:
        reloaded = verify_uow.approvals.get(request.id)
        verify_uow._session.close()
    assert reloaded is not None
    assert reloaded.id == request.id


def test_rollback_discards_staged_approval_and_audit_rows_together(tmp_path):
    factory = _factory(tmp_path)
    request = ApprovalRequest.create(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id="budget-2",
        tenant_id="tenant-a",
        project_id="project-1",
        organization_id="org-a",
        payload={"budget_id": "budget-2"},
        requested_by_user_id="user-1",
        requested_by_username="requester",
    )
    uow = factory.create(context=_context())
    uow.approvals.add(request)
    uow._enterprise_audit_service.record(
        operation="create",
        entity_type="approval_request",
        entity_id=request.id,
        module="platform",
    )
    uow._session.rollback()
    uow._session.close()

    with factory.create(context=_context("verify")) as verify_uow:
        reloaded = verify_uow.approvals.get(request.id)
        from sqlalchemy import text

        audit_row_count = verify_uow._session.execute(
            text("SELECT COUNT(*) FROM audit_entries WHERE entity_id = :eid"),
            {"eid": request.id},
        ).scalar_one()
        verify_uow._session.close()
    assert reloaded is None
    assert audit_row_count == 0


def test_approval_request_mapper_round_trips_tenant_and_organization_id():
    """Approval-P1 (§6): the mapper must round-trip `tenant_id` -- ORM tenant_id=T1/org_id=O1 ->
    domain -> ORM, byte-for-byte unchanged, with no ambient context involved anywhere in the
    mapping functions themselves."""
    from src.core.platform.infrastructure.persistence.mappers.approval.approval import (
        approval_from_orm,
        approval_to_orm,
    )
    from src.core.platform.infrastructure.persistence.orm.approval.approval import (
        ApprovalRequestORM,
    )

    orm = ApprovalRequestORM(
        id="req-1",
        tenant_id="T1",
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id="budget-1",
        organization_id="O1",
        project_id="project-1",
        payload_json="{}",
        status="PENDING",
        requested_by_user_id="user-1",
        requested_by_username="requester",
        requested_at=_dt.datetime(2026, 8, 1, tzinfo=_dt.timezone.utc),
    )
    domain = approval_from_orm(orm)
    assert domain.tenant_id == "T1"
    assert domain.organization_id == "O1"

    round_tripped = approval_to_orm(domain)
    assert round_tripped.tenant_id == "T1"
    assert round_tripped.organization_id == "O1"
    assert round_tripped.id == orm.id
    assert round_tripped.request_type == orm.request_type


def test_cross_tenant_context_cannot_read_another_tenants_approval_request(tmp_path):
    """Approval-P1 (§7): Tenant A's `ApprovalRequest` must not be readable through a UoW whose
    active context resolves to Tenant B -- proven without ever switching an "active
    organization" within the same tenant; the two contexts are genuinely different tenants."""
    from src.core.platform.infrastructure.persistence.unit_of_work import (
        SqlAlchemyPlatformUnitOfWorkFactory,
    )

    engine_path = tmp_path / "cross_tenant.db"
    from sqlalchemy import create_engine as _create_engine
    from sqlalchemy.orm import sessionmaker as _sessionmaker

    engine = _create_engine(f"sqlite:///{engine_path}", future=True)
    Base.metadata.create_all(engine)
    session_factory = _sessionmaker(bind=engine, future=True)

    factory_a = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=session_factory,
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=_FakeTenantContextService(
            tenant_id="tenant-a", organization_id="org-a"
        ),
        user_session=None,
    )
    factory_b = SqlAlchemyPlatformUnitOfWorkFactory(
        session_factory=session_factory,
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=_FakeTenantContextService(
            tenant_id="tenant-b", organization_id="org-b"
        ),
        user_session=None,
    )

    request = ApprovalRequest.create(
        request_type="budget.approve",
        entity_type="project_budget",
        entity_id="budget-cross-tenant",
        tenant_id="tenant-a",
        project_id="project-1",
        organization_id="org-a",
        payload={"budget_id": "budget-cross-tenant"},
        requested_by_user_id="user-1",
        requested_by_username="requester",
    )
    with factory_a.create(context=_context()) as uow_a:
        uow_a.approvals.add(request)
        uow_a.commit()

    with factory_b.create(context=_context("as-tenant-b")) as uow_b:
        assert uow_b.approvals.get(request.id) is None
        assert uow_b.approvals.list_by_status() == []

    with factory_a.create(context=_context("as-tenant-a-verify")) as uow_a_verify:
        reloaded = uow_a_verify.approvals.get(request.id)
        uow_a_verify._session.close()
    assert reloaded is not None
    assert reloaded.id == request.id


def test_platform_uow_never_touches_a_different_shared_session(tmp_path):
    factory = _factory(tmp_path)
    shared_engine = create_engine(f"sqlite:///{tmp_path}/legacy_shared.db", future=True)
    Base.metadata.create_all(shared_engine)
    shared_session = sessionmaker(bind=shared_engine, future=True)()

    with factory.create(context=_context()) as uow:
        assert uow._session is not shared_session
        assert uow._session.bind is not shared_session.bind
        uow.commit()

    assert not shared_session.in_transaction()
    shared_session.close()
