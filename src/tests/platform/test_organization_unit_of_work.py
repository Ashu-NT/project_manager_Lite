"""P4B (Organization Capability Transaction Convergence): `SqlAlchemyOrganizationUnitOfWork`/
`SqlAlchemyOrganizationUnitOfWorkFactory` -- proven directly, mirroring
`test_platform_unit_of_work.py` (Approval's own P4 Step 2 equivalent), before
`OrganizationService` is cut over onto them.
"""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.core.platform.domain.master_data.org import Organization
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM
from src.core.platform.infrastructure.persistence.organization_unit_of_work import (
    SqlAlchemyOrganizationUnitOfWork,
    SqlAlchemyOrganizationUnitOfWorkFactory,
)
from src.core.shared.events.domain_event_context import DomainEventContext
from src.infra.events.in_process_post_commit_event_bus import InProcessPostCommitEventBus
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.orm.base import Base

_TENANT_ID = "tenant-a"


class _FakeTenantContextService:
    def __init__(self, tenant_id=_TENANT_ID, organization_id="org-a"):
        self._tenant_id = tenant_id
        self._organization_id = organization_id

    def require_active_scope_ids(self, *, operation_label):
        from src.core.platform.application.tenant.tenancy.tenant_context import ActiveScopeIds

        return ActiveScopeIds(tenant_id=self._tenant_id, organization_id=self._organization_id)

    def require_active_organization_id(self, *, operation_label):
        return self._organization_id

    def get_active_tenant_id(self):
        return self._tenant_id


def _factory(tmp_path, name="organization_uow.db"):
    engine = create_engine(f"sqlite:///{tmp_path}/{name}", future=True)
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, future=True)
    seed_session = session_factory()
    seed_session.add(TenantORM(id=_TENANT_ID, tenant_code="TENANT-A", display_name="Tenant A", is_active=True, version=1))
    seed_session.commit()
    seed_session.close()
    return SqlAlchemyOrganizationUnitOfWorkFactory(
        session_factory=session_factory,
        transactional_dispatcher=InProcessTransactionalEventDispatcher(),
        post_commit_bus=InProcessPostCommitEventBus(),
        tenant_context_service=_FakeTenantContextService(),
        user_session=None,
    )


def _context(correlation_id="corr-1"):
    return DomainEventContext(correlation_id=correlation_id)


def _organization(code="NORTH"):
    return Organization.create(
        organization_code=code,
        display_name="North Division",
        tenant_id=_TENANT_ID,
    )


def test_create_returns_an_organization_unit_of_work_with_organizations_and_audit_bound_to_a_fresh_session(
    tmp_path,
):
    factory = _factory(tmp_path)
    uow = factory.create(context=_context())
    assert isinstance(uow, SqlAlchemyOrganizationUnitOfWork)
    assert uow.organizations.session is uow._session
    assert uow._enterprise_audit_service._session is uow._session
    uow._session.close()


def test_two_create_calls_open_genuinely_independent_sessions(tmp_path):
    factory = _factory(tmp_path)
    uow1 = factory.create(context=_context("c1"))
    uow2 = factory.create(context=_context("c2"))
    assert uow1._session is not uow2._session
    assert uow1.organizations is not uow2.organizations
    assert uow1.organizations.session is not uow2.organizations.session
    uow1._session.close()
    uow2._session.close()


def test_organization_commits_via_the_organization_uow(tmp_path):
    factory = _factory(tmp_path)
    organization = _organization()
    with factory.create(context=_context()) as uow:
        uow.organizations.add(organization)
        uow.commit()

    with factory.create(context=_context("verify")) as verify_uow:
        reloaded = verify_uow.organizations.get(organization.id)
        verify_uow._session.close()
    assert reloaded is not None
    assert reloaded.id == organization.id


def test_rollback_discards_staged_organization_and_audit_rows_together(tmp_path):
    factory = _factory(tmp_path)
    organization = _organization(code="ROLLBACK")
    uow = factory.create(context=_context())
    uow.organizations.add(organization)
    uow._enterprise_audit_service.record(
        operation="create",
        entity_type="organization",
        entity_id=organization.id,
        module="platform",
    )
    uow._session.rollback()
    uow._session.close()

    with factory.create(context=_context("verify")) as verify_uow:
        reloaded = verify_uow.organizations.get(organization.id)
        audit_row_count = verify_uow._session.execute(
            text("SELECT COUNT(*) FROM audit_entries WHERE entity_id = :eid"),
            {"eid": organization.id},
        ).scalar_one()
        verify_uow._session.close()
    assert reloaded is None
    assert audit_row_count == 0


def test_organization_uow_never_touches_a_different_shared_session(tmp_path):
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
