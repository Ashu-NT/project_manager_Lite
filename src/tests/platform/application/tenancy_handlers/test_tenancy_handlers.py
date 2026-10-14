from __future__ import annotations

import inspect
import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from src.core.platform.api.desktop.tenant.tenancy.tenant import PlatformTenantDesktopApi
from src.core.platform.application.tenant.tenancy import (
    TenantAdminQueryHandler,
    TenantInvitationCommandHandler,
    TenantLifecycleCommandHandler,
    TenantMembershipLifecycleCommandHandler,
    TenantMembershipQueryHandler,
    hash_invitation_token,
)
from src.core.platform.application.tenant.tenancy.tenant_context import (
    TenantContextService,
)
from src.core.platform.common.exceptions import BusinessRuleError
from src.core.platform.domain.security.auth import (
    AuthSession,
    Role,
    UserAccount,
    UserSessionContext,
    UserSessionPrincipal,
)
from src.core.platform.domain.security.authorization.roles import (
    RoleBindingAssigned,
    RoleBindingRevoked,
)
from src.core.platform.domain.tenant.tenancy import (
    Tenant,
    TenantInvitationChanged,
    TenantMembershipActivated,
    TenantMembershipRemoved,
    TenantMembershipSuspended,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.admin import (
    build_tenant_admin_dependencies,
)
from src.core.platform.infrastructure.composition.dependencies.tenancy.membership import (
    build_tenant_membership_dependencies,
)
from src.core.platform.infrastructure.persistence.orm.history.audit.audit_entry import (
    AuditEntryORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.department.departments import (
    DepartmentORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.employee.employee import (
    EmployeeORM,
)
from src.core.platform.infrastructure.persistence.orm.master_data.org.org import (
    OrganizationORM,
)
from src.core.platform.infrastructure.persistence.orm.security.auth.auth import UserORM
from src.core.platform.infrastructure.persistence.repositories.history.platform_events.platform_events import (
    SqlAlchemyPlatformEventRepository,
)
from src.core.platform.infrastructure.persistence.repositories.security.auth.auth import (
    SqlAlchemyAuthSessionRepository,
    SqlAlchemyRoleBindingRepository,
    SqlAlchemyRoleRepository,
    SqlAlchemyUserRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
    SqlAlchemyTenantRepository,
)
from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.infra.events.in_process_post_commit_event_bus import (
    InProcessPostCommitEventBus,
)
from src.infra.events.in_process_transactional_event_dispatcher import (
    InProcessTransactionalEventDispatcher,
)
from src.infra.persistence.orm.base import Base


def _principal(user_id, *, admin=False):
    return UserSessionPrincipal(
        user_id=user_id,
        username=user_id,
        display_name=user_id,
        role_names=frozenset({"admin"} if admin else {"viewer"}),
        permissions=frozenset({"platform.admin", "auth.manage"} if admin else set()),
    )


@pytest.fixture
def tenancy():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    session = sessions()
    tenants = SqlAlchemyTenantRepository(session)
    tenant = Tenant.create("HANDLERS", "Handler Tenant")
    tenants.add(tenant)
    users = SqlAlchemyUserRepository(session)
    for user_id in ("admin-user", "recipient", "other-user"):
        users.add(
            UserAccount(
                id=user_id,
                username=user_id,
                password_hash="hashed-password",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    roles = SqlAlchemyRoleRepository(session)
    roles.add(Role.create("viewer"))
    session.commit()
    session.add(
        OrganizationORM(
            id="organization",
            tenant_id=tenant.id,
            organization_code="ORG",
            display_name="Organization",
        )
    )
    session.flush()
    session.add(
        DepartmentORM(
            id="department",
            tenant_id=tenant.id,
            organization_id="organization",
            department_code="DEPT",
            name="Department",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
    )
    session.flush()
    session.add(
        EmployeeORM(
            id="employee",
            tenant_id=tenant.id,
            organization_id="organization",
            department_id="department",
            employee_code="EMP",
            full_name="Recipient",
            user_id="recipient",
        )
    )
    session.commit()
    user_session = UserSessionContext()
    user_session.set_principal(_principal("admin-user", admin=True))
    user_session.set_active_tenant_id(tenant.id)
    context = Mock(spec=TenantContextService)
    context.require_active_tenant_id.return_value = tenant.id
    dispatcher = InProcessTransactionalEventDispatcher()
    bus = InProcessPostCommitEventBus()
    published = []
    for event_type in (
        TenantInvitationChanged,
        TenantMembershipActivated,
        TenantMembershipRemoved,
        TenantMembershipSuspended,
        RoleBindingAssigned,
        RoleBindingRevoked,
    ):
        bus.subscribe(event_type, lambda emitted, _context: published.append(emitted))
    membership = build_tenant_membership_dependencies(
        session=session,
        user_session=user_session,
        tenant_context_service=context,
        scope_resolvers=SimpleNamespace(organization_owner={}),
        transactional_dispatcher=dispatcher,
        post_commit_bus=bus,
    )
    admin = build_tenant_admin_dependencies(
        session=session,
        user_session=user_session,
        repositories=SimpleNamespace(
            tenant_repo=tenants,
            user_tenant_repo=SqlAlchemyUserTenantMembershipRepository(session),
            platform_event_repo=SqlAlchemyPlatformEventRepository(session),
        ),
    )
    try:
        yield SimpleNamespace(
            session=session,
            sessions=sessions,
            tenant=tenant,
            user_session=user_session,
            context=context,
            dispatcher=dispatcher,
            published=published,
            membership=membership,
            admin=admin,
        )
    finally:
        session.close()
        engine.dispose()


def _issue(tenancy):
    return tenancy.membership.tenant_invitation_commands.issue_invitation(
        "recipient",
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )


def _membership(tenancy):
    with tenancy.sessions() as session:
        return SqlAlchemyUserTenantMembershipRepository(session).get(
            "recipient", tenancy.tenant.id
        )


def test_composition_exposes_only_explicit_operation_groups(tenancy):
    admin = tenancy.admin
    membership = tenancy.membership
    assert isinstance(admin.tenant_admin_queries, TenantAdminQueryHandler)
    assert isinstance(admin.tenant_lifecycle_commands, TenantLifecycleCommandHandler)
    assert isinstance(
        membership.tenant_invitation_commands, TenantInvitationCommandHandler
    )
    assert isinstance(
        membership.tenant_membership_queries, TenantMembershipQueryHandler
    )
    assert isinstance(
        membership.tenant_membership_lifecycle_commands,
        TenantMembershipLifecycleCommandHandler,
    )
    assert not hasattr(admin, "create_tenant")
    assert not hasattr(membership, "accept_invitation")
    assert not hasattr(membership.tenant_membership_queries, "remove_member")


def test_invitation_token_is_external_only_and_acceptance_order_is_atomic(tenancy):
    issued = _issue(tenancy)
    assert _membership(tenancy).invitation_token_hash == hash_invitation_token(
        issued.token
    )
    assert issued.token not in json.dumps(asdict(tenancy.published[0]), default=str)
    tenancy.published.clear()
    tenancy.user_session.set_principal(_principal("recipient"))
    pending = tenancy.membership.tenant_membership_queries.list_my_pending_invitations()
    assert [item.id for item in pending] == [issued.membership.id]
    accepted = tenancy.membership.tenant_invitation_commands.accept_invitation(
        issued.token
    )
    assert accepted.status == "active"
    assert accepted.invitation_token_hash is None
    assert [type(item) for item in tenancy.published] == [
        TenantMembershipActivated,
        RoleBindingAssigned,
    ]
    with tenancy.sessions() as session:
        assert (
            len(
                SqlAlchemyRoleBindingRepository(session).list_active_for_principal(
                    "recipient", tenant_id=tenancy.tenant.id
                )
            )
            == 1
        )
        audits = session.scalars(
            select(AuditEntryORM).where(AuditEntryORM.entity_id == accepted.id)
        ).all()
        assert len(audits) == 2
        assert issued.token not in str([row.metadata_json for row in audits])
    with pytest.raises(BusinessRuleError):
        tenancy.membership.tenant_invitation_commands.accept_invitation(issued.token)


def test_acceptance_failure_rolls_back_membership_role_audit_and_publication(tenancy):
    issued = _issue(tenancy)
    tenancy.published.clear()
    tenancy.user_session.set_principal(_principal("recipient"))

    def fail_role_grant(_event, _uow):
        raise RuntimeError("transactional grant failure")

    tenancy.dispatcher.subscribe(RoleBindingAssigned, fail_role_grant)
    with pytest.raises(RuntimeError, match="transactional grant failure"):
        tenancy.membership.tenant_invitation_commands.accept_invitation(issued.token)
    assert _membership(tenancy).status == "invited"
    assert _membership(tenancy).invitation_token_hash == hash_invitation_token(
        issued.token
    )
    assert tenancy.published == []
    with tenancy.sessions() as session:
        assert (
            SqlAlchemyRoleBindingRepository(session).list_active_for_principal(
                "recipient", tenant_id=tenancy.tenant.id
            )
            == []
        )
        assert (
            len(
                session.scalars(
                    select(AuditEntryORM).where(
                        AuditEntryORM.entity_id == issued.membership.id
                    )
                ).all()
            )
            == 1
        )


def test_pending_queries_and_acceptance_are_recipient_scoped(tenancy):
    issued = _issue(tenancy)
    tenancy.user_session.set_principal(_principal("other-user"))
    assert (
        tenancy.membership.tenant_membership_queries.list_my_pending_invitations() == []
    )
    with pytest.raises(BusinessRuleError) as denied:
        tenancy.membership.tenant_invitation_commands.accept_invitation(issued.token)
    assert denied.value.code == "TENANT_INVITATION_TARGET_MISMATCH"
    assert _membership(tenancy).status == "invited"


def test_invitation_revocation_is_not_member_removal(tenancy):
    _issue(tenancy)
    tenancy.published.clear()
    revoked = tenancy.membership.tenant_invitation_commands.revoke_invitation(
        "recipient"
    )
    assert revoked.status == "removed"
    assert [type(item) for item in tenancy.published] == [TenantInvitationChanged]
    assert tenancy.published[0].change_type == "revoked"


def test_membership_lifecycle_preserves_account_and_revokes_roles_in_order(tenancy):
    issued = _issue(tenancy)
    tenancy.user_session.set_principal(_principal("recipient"))
    tenancy.membership.tenant_invitation_commands.accept_invitation(issued.token)
    tenancy.user_session.set_principal(_principal("admin-user", admin=True))
    durable_session = AuthSession.create(
        user_id="recipient",
        session_revision=1,
        auth_method="password",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        last_active_tenant_id=tenancy.tenant.id,
    )
    SqlAlchemyAuthSessionRepository(tenancy.session).add(durable_session)
    tenancy.session.commit()
    lifecycle = tenancy.membership.tenant_membership_lifecycle_commands
    assert lifecycle.suspend_member("recipient").status == "suspended"
    with tenancy.sessions() as session:
        assert (
            SqlAlchemyAuthSessionRepository(session).get(durable_session.id).revoked_at
            is not None
        )
        assert (
            len(
                SqlAlchemyRoleBindingRepository(session).list_active_for_principal(
                    "recipient", tenant_id=tenancy.tenant.id
                )
            )
            == 1
        )
    assert lifecycle.reactivate_member("recipient").status == "active"
    tenancy.published.clear()
    assert lifecycle.remove_member("recipient").status == "removed"
    assert [type(item) for item in tenancy.published] == [
        TenantMembershipRemoved,
        RoleBindingRevoked,
    ]
    with tenancy.sessions() as session:
        assert session.get(UserORM, "recipient").is_active
        assert session.get(EmployeeORM, "employee").user_id == "recipient"
        assert (
            SqlAlchemyRoleBindingRepository(session).list_active_for_principal(
                "recipient", tenant_id=tenancy.tenant.id
            )
            == []
        )


def test_admin_lifecycle_permissions_events_and_self_lockout(tenancy):
    commands = tenancy.admin.tenant_lifecycle_commands
    tenant = commands.create_tenant("NEW-TENANT", "New Tenant")
    assert commands.suspend_tenant(tenant.id).tenant_status == "suspended"
    assert commands.archive_tenant(tenant.id).tenant_status == "archived"
    assert commands.restore_tenant(tenant.id).tenant_status == "active"
    events = SqlAlchemyPlatformEventRepository(tenancy.session).list_for_tenant(
        tenant.id
    )
    assert {item.operation for item in events} == {
        "create_tenant",
        "suspend_tenant",
        "archive_tenant",
        "restore_tenant",
    }
    with pytest.raises(BusinessRuleError) as lockout:
        commands.suspend_tenant(tenancy.tenant.id)
    assert lockout.value.code == "TENANT_SELF_LOCKOUT"
    tenancy.user_session.set_principal(_principal("recipient"))
    with pytest.raises(BusinessRuleError):
        commands.create_tenant("DENIED", "Denied")
    with pytest.raises(BusinessRuleError):
        tenancy.admin.tenant_admin_queries.list_tenants()


def test_desktop_api_requires_and_uses_direct_handlers(tenancy):
    issued = _issue(tenancy)
    tenancy.user_session.set_principal(_principal("recipient"))
    api = PlatformTenantDesktopApi(
        tenant_admin_queries=tenancy.admin.tenant_admin_queries,
        tenant_lifecycle_commands=tenancy.admin.tenant_lifecycle_commands,
        tenant_context_service=tenancy.context,
        tenant_invitation_commands=tenancy.membership.tenant_invitation_commands,
        tenant_membership_queries=tenancy.membership.tenant_membership_queries,
    )
    pending = api.list_pending_invitations()
    assert pending.ok
    assert [item.membership_id for item in pending.data] == [issued.membership.id]
    assert api.accept_invitation(tenancy.tenant.id).ok
    assert api.list_accessible_tenants().data[0].id == tenancy.tenant.id
    parameters = inspect.signature(PlatformTenantDesktopApi).parameters
    assert all(
        parameter.default is inspect.Parameter.empty
        for parameter in parameters.values()
    )
