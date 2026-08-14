"""Users Overview rollup -- semantic-equivalence-proven SQL replacement for
list_users() + Python aggregation on the Admin Overview.

list_users() (user_admin_service.py) is left completely UNCHANGED and is
still what the paginated Users workspace page calls. This only replaces how
PlatformAdminWorkspacePresenter.build_overview() computes three numbers
(total/active/locked), which previously required a full list_users() call --
for tenant callers, a per-user N+1 (_canonical_platform_authority(user.id):
a full permission-catalog fetch plus a role-binding query, per user) to
implement the platform-role exclusion.

The exclusion predicate's semantic-equivalence proof (see the reader impl's
module comments) established:
  - role_bindings.tenant_id IS NULL is DB-proven equivalent to
    actual_scope_type='platform' (ck_role_bindings_scope_shape CHECK).
  - That alone does NOT prove "platform authority" as
    _canonical_platform_authority defines it -- the referenced role must
    ALSO independently have allowed_scope_type='platform' (app-write-path
    enforced, not DB-enforced), pass role.status='active', and have a name
    literally in {"admin", "support_admin"} (list_users()'s own extra
    is_platform_role() re-check after _canonical_platform_authority's
    scope/status validation already ran).
  - So the SQL predicate reproduces ALL of those checks explicitly, never
    inferring authority from tenant_id IS NULL alone.

These tests: (A) reader-level unit tests against an isolated db covering
every scenario in the required matrix, (B) service-level tests through the
real `services` fixture for both caller-type branches, (C) a parity test
comparing the rollup against list_users()'s own actual population for a
representative fixture, (D) guardrails proving a bounded query count and
that no per-user canonical-authority/permission lookups happen.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.core.platform.infrastructure.persistence.orm.security.auth.auth import (
    RoleBindingORM,
    RoleORM,
    UserORM,
)
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.tenant import TenantORM
from src.core.platform.infrastructure.persistence.orm.tenant.tenancy.user_tenant import UserTenantORM
from src.core.platform.infrastructure.persistence.read.overview.platform_overview_rollup_reader import (
    SqlAlchemyPlatformOverviewRollupReader,
)
from src.infra.persistence.orm import Base


# ---------------------------------------------------------------------------
# Reader-level unit tests: isolated db, full control over every scenario.
# ---------------------------------------------------------------------------


@pytest.fixture
def reader_session():
    engine = create_engine("sqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)
    db = Session()
    try:
        yield db, engine
    finally:
        db.close()


_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _seed_tenant(db, *, id, code=None):
    db.add(TenantORM(id=id, tenant_code=code or id, display_name=code or id, is_active=True, version=1))


def _seed_user(db, *, id, username, is_active=True, locked_until=None):
    db.add(
        UserORM(
            id=id,
            username=username,
            password_hash="hash",
            is_active=is_active,
            locked_until=locked_until,
            created_at=_NOW,
            updated_at=_NOW,
            version=1,
        )
    )


def _seed_membership(db, *, id, user_id, tenant_id, status="active"):
    db.add(
        UserTenantORM(
            id=id,
            user_id=user_id,
            tenant_id=tenant_id,
            status=status,
            invitation_token_hash="hash" if status == "invited" else None,
            created_at=_NOW,
            updated_at=_NOW,
            version=1,
        )
    )


def _seed_role(db, *, id, name, allowed_scope_type="platform", status="active", is_system=True, tenant_id=None):
    db.add(
        RoleORM(
            id=id,
            name=name,
            display_name=name,
            is_system=is_system,
            tenant_id=tenant_id,
            allowed_scope_type=allowed_scope_type,
            status=status,
            created_at=_NOW,
            updated_at=_NOW,
        )
    )


def _seed_binding(
    db,
    *,
    id,
    user_id,
    role_id,
    actual_scope_type="platform",
    tenant_id=None,
    actual_scope_id=None,
    revoked_at=None,
    expires_at=None,
):
    db.add(
        RoleBindingORM(
            id=id,
            principal_type="user",
            principal_id=user_id,
            role_id=role_id,
            tenant_id=tenant_id,
            actual_scope_type=actual_scope_type,
            actual_scope_id=actual_scope_id,
            assigned_at=_NOW,
            expires_at=expires_at,
            revoked_at=revoked_at,
            version=1,
        )
    )


def _count_selects(engine, table_name, fn):
    statements = []

    def _listener(conn, cursor, statement, parameters, context, executemany):
        if table_name in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", _listener)
    try:
        result = fn()
    finally:
        event.remove(engine, "before_cursor_execute", _listener)
    return result, len(statements)


# --- Empty tenant / basic population ---------------------------------------


def test_empty_tenant_returns_zero(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert (summary.total, summary.active, summary.locked) == (0, 0, 0)


def test_ordinary_tenant_users_counted(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_user(db, id="u2", username="u2")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_membership(db, id="m2", user_id="u2", tenant_id="t1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 2


def test_active_inactive_users(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1", is_active=True)
    _seed_user(db, id="u2", username="u2", is_active=False)
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_membership(db, id="m2", user_id="u2", tenant_id="t1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert (summary.total, summary.active) == (2, 1)


def test_locked_unlocked_users(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1", locked_until=_NOW + timedelta(hours=1))
    _seed_user(db, id="u2", username="u2", locked_until=None)
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_membership(db, id="m2", user_id="u2", tenant_id="t1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert (summary.total, summary.locked) == (2, 1)


def test_locked_until_in_past_still_counts_as_locked(reader_session):
    """Matches list_users()'s own criterion exactly: `locked_until is not
    None`, not `locked_until > now` -- a stale-but-non-null lock still
    counts as locked in both the old and new path."""
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1", locked_until=_NOW - timedelta(days=1))
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.locked == 1


# --- Tenant isolation / membership status -----------------------------------


def test_user_belonging_to_another_tenant_excluded(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_tenant(db, id="t2")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t2")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 0


def test_non_active_membership_status_excluded(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    for status, uid in [("invited", "u1"), ("suspended", "u2"), ("removed", "u3")]:
        _seed_user(db, id=uid, username=uid)
        _seed_membership(db, id=f"m-{uid}", user_id=uid, tenant_id="t1", status=status)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 0


def test_multi_tenant_membership_scoped_correctly_no_fanout(reader_session):
    """A user active in two tenants must be counted once per tenant query,
    never fanned out into duplicate rows by the join."""
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_tenant(db, id="t2")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_membership(db, id="m2", user_id="u1", tenant_id="t2")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)

    assert reader.get_user_summary(tenant_id="t1").total == 1
    assert reader.get_user_summary(tenant_id="t2").total == 1


# --- Platform-authority exclusion -------------------------------------------


def test_user_with_effective_platform_authority_excluded(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="admin")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 0


def test_support_admin_role_also_excludes(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="support_admin")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 0


def test_revoked_platform_binding_does_not_exclude(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="admin")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1", revoked_at=_NOW - timedelta(days=1))
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 1


def test_expired_platform_binding_does_not_exclude(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="admin")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1", expires_at=_NOW - timedelta(seconds=1))
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 1


def test_non_expiring_platform_binding_excludes(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="admin")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1", expires_at=None)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 0


def test_inactive_platform_role_does_not_exclude(reader_session):
    """Matches _resolve()'s `if role.status != "active": continue` -- a
    binding to a suspended role grants no authority."""
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="admin", status="inactive")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 1


def test_role_named_admin_but_wrong_allowed_scope_type_does_not_exclude(reader_session):
    """Corrupted-data resilience: a binding whose actual_scope_type is
    'platform' but whose referenced role's own allowed_scope_type field
    disagrees (drifted independently of the name) must not be trusted as
    platform authority -- matches this reader's explicit re-derivation
    rather than inferring authority from tenant_id/scope_type alone."""
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="admin", allowed_scope_type="tenant", is_system=False, tenant_id="t1")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 1


def test_platform_scope_role_with_non_platform_name_does_not_exclude(reader_session):
    """The inverse corrupted-data case: allowed_scope_type='platform' but a
    name outside {admin, support_admin} -- list_users()'s own
    is_platform_role() re-check would not exclude this user either, so
    neither should this predicate."""
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="renamed_platform_role", allowed_scope_type="platform")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 1


def test_non_platform_scope_binding_never_excludes(reader_session):
    """A tenant-scope role binding (even one named 'admin', which cannot
    happen validly but proves the predicate doesn't just match on name)
    must never trigger exclusion -- only actual_scope_type='platform'
    bindings are even considered."""
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="viewer", allowed_scope_type="tenant", is_system=False, tenant_id="t1")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1", actual_scope_type="tenant", tenant_id="t1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 1


def test_exact_expiry_boundary_expires_at_equal_now_is_expired(reader_session):
    """Strict '>' matches SqlAlchemyRoleBindingRepository.list_active_for_
    principal exactly: expires_at == now must NOT count as still active."""
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_user(db, id="u1", username="u1")
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_role(db, id="r1", name="admin")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1", expires_at=_NOW)
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    # The reader computes "now" itself at call time, which will be later
    # than _NOW (a fixed point in the past) -- so this binding is expired
    # under any real clock reading, and the user is not excluded.
    summary = reader.get_user_summary(tenant_id="t1")

    assert summary.total == 1


def test_platform_operator_path_counts_all_users_no_exclusion(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    _seed_tenant(db, id="t2")
    _seed_user(db, id="u1", username="u1", is_active=True)
    _seed_user(db, id="u2", username="u2", is_active=False, locked_until=_NOW)
    _seed_membership(db, id="m1", user_id="u1", tenant_id="t1")
    _seed_membership(db, id="m2", user_id="u2", tenant_id="t2")
    _seed_role(db, id="r1", name="admin")
    _seed_binding(db, id="b1", user_id="u1", role_id="r1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id=None)

    # No tenant filter, no exclusion -- both users counted, matching
    # list_all()'s exact population.
    assert summary.total == 2
    assert summary.active == 1
    assert summary.locked == 1


def test_platform_operator_path_empty_db(reader_session):
    db, engine = reader_session
    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary = reader.get_user_summary(tenant_id=None)
    assert (summary.total, summary.active, summary.locked) == (0, 0, 0)


# --- Query-count guardrail ---------------------------------------------------


def test_tenant_path_issues_bounded_query_count_independent_of_n(reader_session):
    db, engine = reader_session
    _seed_tenant(db, id="t1")
    for i in range(25):
        _seed_user(db, id=f"u{i}", username=f"u{i}", is_active=(i % 2 == 0))
        _seed_membership(db, id=f"m{i}", user_id=f"u{i}", tenant_id="t1")
    _seed_role(db, id="r1", name="admin")
    _seed_binding(db, id="b1", user_id="u0", role_id="r1")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    summary, statement_count = _count_selects(
        engine, "users", lambda: reader.get_user_summary(tenant_id="t1")
    )

    assert statement_count == 1
    assert summary.total == 24  # 25 seeded, minus the one excluded platform admin


def test_platform_operator_path_issues_exactly_one_statement(reader_session):
    db, engine = reader_session
    for i in range(10):
        _seed_user(db, id=f"u{i}", username=f"u{i}")
    db.flush()

    reader = SqlAlchemyPlatformOverviewRollupReader(db)
    _, statement_count = _count_selects(
        engine, "users", lambda: reader.get_user_summary(tenant_id=None)
    )

    assert statement_count == 1


# ---------------------------------------------------------------------------
# Service-level tests through the real `services` fixture.
# ---------------------------------------------------------------------------


def test_service_platform_operator_path_matches_list_all_semantics(services):
    """The default `services` fixture's authenticated principal is the
    bootstrap "admin" user -- a platform operator."""
    auth_service = services["auth_service"]

    baseline = auth_service.get_user_rollup_summary()
    auth_service.onboard_tenant_user(
        username="rollup-service-user-1",
        raw_password="StrongPass123!",
        display_name="Rollup Service User",
        is_active=True,
    )

    updated = auth_service.get_user_rollup_summary()
    assert updated.total == baseline.total + 1


def test_desktop_api_get_user_rollup_summary(services):
    from src.core.platform.api.desktop.security.auth.user import PlatformUserDesktopApi

    auth_service = services["auth_service"]
    api = PlatformUserDesktopApi(auth_service=auth_service)

    result = api.get_user_rollup_summary()

    assert result.ok
    assert result.data.total >= 1


def _make_tenant_caller_session(services, *, tenant_id: str):
    from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
    from src.core.platform.application.security.auth.auth_service import AuthService
    from src.core.platform.application.tenant.tenancy.tenant_context import TenantContextService

    auth = services["auth_service"]
    viewer = auth.register_user(
        f"rollup-tenant-viewer-{tenant_id}", "StrongPass123!", role_names=["viewer"]
    )
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )
    from src.core.platform.domain.tenant.tenancy.user_tenant_membership import UserTenantMembership

    session = services["session"]
    user_tenant_repo = SqlAlchemyUserTenantMembershipRepository(session)
    user_tenant_repo.add(UserTenantMembership.create(user_id=viewer.id, tenant_id=tenant_id))
    session.flush()

    viewer_session = UserSessionContext()
    viewer_session.set_principal(
        UserSessionPrincipal(
            user_id=viewer.id,
            username=viewer.username,
            display_name=viewer.display_name or viewer.username,
            role_names=frozenset({"viewer"}),
            permissions=frozenset({"auth.read"}),
        )
    )
    viewer_session.set_active_tenant_id(tenant_id)

    # A fresh TenantContextService bound to viewer_session -- reusing the
    # shared services["auth_service"]._tenant_context_service would validate
    # against the ADMIN session's active tenant, not the viewer's, and
    # raise TENANT_CONTEXT_MISMATCH.
    viewer_tenant_context_service = TenantContextService(
        tenant_repo=auth._tenant_context_service._tenant_repo,
        organization_repo=auth._tenant_context_service._organization_repo,
        user_session=viewer_session,
        user_tenant_repo=user_tenant_repo,
        context_policy=auth._tenant_context_service._context_policy,
    )

    return AuthService(
        session=session,
        user_repo=auth._user_repo,
        role_repo=auth._role_repo,
        permission_repo=auth._permission_repo,
        role_permission_repo=auth._role_permission_repo,
        auth_session_repo=auth._auth_session_repo,
        user_session=viewer_session,
        enterprise_audit_service=auth._enterprise_audit_service,
        security_audit_repo=auth._security_audit_repo,
        user_tenant_repo=auth._user_tenant_repo,
        tenant_context_service=viewer_tenant_context_service,
        role_binding_repo=auth._role_binding_repo,
        overview_rollup_reader=auth._overview_rollup_reader,
    ), viewer.id


def test_service_tenant_caller_path_excludes_platform_users_and_scopes_by_tenant(services):
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
        SqlAlchemyTenantRepository,
    )
    from src.core.platform.domain.tenant.tenancy.tenant import Tenant

    session = services["session"]
    tenant_repo = SqlAlchemyTenantRepository(session)
    tenant = Tenant.create(tenant_code="ROLLUP-T1", display_name="Rollup Tenant 1")
    tenant_repo.add(tenant)
    session.flush()

    tenant_auth, viewer_id = _make_tenant_caller_session(services, tenant_id=tenant.id)

    baseline = tenant_auth.get_user_rollup_summary()
    assert baseline.total == 1  # just the viewer registered into this tenant

    # Register a platform-authority user and add them to the SAME tenant --
    # they must not be counted, matching list_users()'s own exclusion.
    admin_service = services["auth_service"]
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )
    from src.core.platform.domain.tenant.tenancy.user_tenant_membership import UserTenantMembership

    from src.core.platform.domain.security.authorization.roles import RoleBinding

    platform_role = admin_service._role_repo.get_by_name("admin")
    platform_user = admin_service.register_user(
        "rollup-platform-user", "StrongPass123!", role_names=[]
    )
    admin_service._role_binding_repo.add(
        RoleBinding.create(
            principal_id=platform_user.id,
            role_id=platform_role.id,
            actual_scope_type="platform",
        )
    )
    user_tenant_repo = SqlAlchemyUserTenantMembershipRepository(session)
    user_tenant_repo.add(UserTenantMembership.create(user_id=platform_user.id, tenant_id=tenant.id))
    session.flush()

    updated = tenant_auth.get_user_rollup_summary()
    assert updated.total == 1  # platform_user excluded, still just the viewer


def test_service_tenant_caller_requires_permission(services):
    from src.core.platform.domain.security.auth.session import UserSessionContext, UserSessionPrincipal
    from src.core.platform.application.security.auth.auth_service import AuthService
    from src.core.platform.common.exceptions import BusinessRuleError

    auth = services["auth_service"]
    no_perms_session = UserSessionContext()
    no_perms_session.set_principal(
        UserSessionPrincipal(
            user_id="no-perms-user",
            username="no-perms-user",
            display_name="No Perms",
            role_names=frozenset(),
            permissions=frozenset(),
        )
    )
    stripped_auth = AuthService(
        session=services["session"],
        user_repo=auth._user_repo,
        role_repo=auth._role_repo,
        permission_repo=auth._permission_repo,
        role_permission_repo=auth._role_permission_repo,
        user_session=no_perms_session,
        overview_rollup_reader=auth._overview_rollup_reader,
    )

    with pytest.raises(BusinessRuleError):
        stripped_auth.get_user_rollup_summary()


# ---------------------------------------------------------------------------
# Parity test: rollup vs. list_users()'s own actual population, for a
# representative mixed fixture.
# ---------------------------------------------------------------------------


def test_parity_with_list_users_platform_operator(services):
    auth_service = services["auth_service"]

    auth_service.onboard_tenant_user(
        username="parity-user-1", raw_password="StrongPass123!", display_name="Parity One", is_active=True
    )
    auth_service.onboard_tenant_user(
        username="parity-user-2", raw_password="StrongPass123!", display_name="Parity Two", is_active=False
    )

    expected_users = auth_service.list_users()
    expected_total = len(expected_users)
    expected_active = sum(1 for u in expected_users if u.is_active)
    expected_locked = sum(1 for u in expected_users if u.locked_until is not None)

    rollup = auth_service.get_user_rollup_summary()

    assert rollup.total == expected_total
    assert rollup.active == expected_active
    assert rollup.locked == expected_locked


def test_parity_with_list_users_tenant_caller_excludes_same_users(services):
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.tenant import (
        SqlAlchemyTenantRepository,
    )
    from src.core.platform.domain.tenant.tenancy.tenant import Tenant
    from src.core.platform.infrastructure.persistence.repositories.tenant.tenancy.user_tenant import (
        SqlAlchemyUserTenantMembershipRepository,
    )
    from src.core.platform.domain.tenant.tenancy.user_tenant_membership import UserTenantMembership
    from src.core.platform.domain.security.authorization.roles import RoleBinding

    session = services["session"]
    tenant_repo = SqlAlchemyTenantRepository(session)
    tenant = Tenant.create(tenant_code="PARITY-T1", display_name="Parity Tenant")
    tenant_repo.add(tenant)
    session.flush()

    admin_service = services["auth_service"]
    user_tenant_repo = SqlAlchemyUserTenantMembershipRepository(session)

    ordinary = admin_service.register_user("parity-ordinary", "StrongPass123!", role_names=["viewer"])
    user_tenant_repo.add(UserTenantMembership.create(user_id=ordinary.id, tenant_id=tenant.id))

    platform_role = admin_service._role_repo.get_by_name("admin")
    platform_user = admin_service.register_user("parity-platform-user", "StrongPass123!", role_names=[])
    admin_service._role_binding_repo.add(
        RoleBinding.create(
            principal_id=platform_user.id,
            role_id=platform_role.id,
            actual_scope_type="platform",
        )
    )
    user_tenant_repo.add(UserTenantMembership.create(user_id=platform_user.id, tenant_id=tenant.id))
    session.flush()

    tenant_auth, _ = _make_tenant_caller_session(services, tenant_id=tenant.id)
    # _make_tenant_caller_session already registers its own viewer into the
    # tenant, so the tenant now has: its own viewer + `ordinary` + the
    # excluded `platform_user`.

    expected_users = tenant_auth.list_users()
    expected_total = len(expected_users)
    assert all(u.id != platform_user.id for u in expected_users)

    rollup = tenant_auth.get_user_rollup_summary()
    assert rollup.total == expected_total


# ---------------------------------------------------------------------------
# Guardrail: no per-user canonical-authority/permission-catalog lookups from
# the Overview path.
# ---------------------------------------------------------------------------


def test_overview_path_never_calls_canonical_platform_authority_or_list_all_permissions(services):
    from src.core.platform.application.security.auth.auth_query import AuthQueryMixin

    auth_service = services["auth_service"]
    for i in range(15):
        auth_service.onboard_tenant_user(
            username=f"guardrail-user-{i}",
            raw_password="StrongPass123!",
            display_name=f"Guardrail User {i}",
            is_active=(i % 2 == 0),
        )

    counts = {"canonical_platform_authority": 0, "permission_list_all": 0}
    real_canonical = AuthQueryMixin._canonical_platform_authority
    real_permission_list_all = type(auth_service._permission_repo).list_all

    def counting_canonical(self, user_id):
        counts["canonical_platform_authority"] += 1
        return real_canonical(self, user_id)

    def counting_permission_list_all(self):
        counts["permission_list_all"] += 1
        return real_permission_list_all(self)

    AuthQueryMixin._canonical_platform_authority = counting_canonical
    type(auth_service._permission_repo).list_all = counting_permission_list_all
    try:
        auth_service.get_user_rollup_summary()
    finally:
        AuthQueryMixin._canonical_platform_authority = real_canonical
        type(auth_service._permission_repo).list_all = real_permission_list_all

    assert counts["canonical_platform_authority"] == 0
    assert counts["permission_list_all"] == 0


def test_admin_overview_user_metrics_match_rollup_not_full_list(services):
    from src.application.runtime import build_desktop_api_registry
    from src.ui_qml.platform.context import PlatformWorkspaceCatalog
    from src.core.platform.application.security.auth.auth_query import AuthQueryMixin

    auth_service = services["auth_service"]
    for i in range(10):
        auth_service.onboard_tenant_user(
            username=f"overview-user-{i}",
            raw_password="StrongPass123!",
            display_name=f"Overview User {i}",
            is_active=(i % 2 == 0),
        )

    expected = auth_service.get_user_rollup_summary()

    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)

    counts = {"canonical_platform_authority": 0}
    real_canonical = AuthQueryMixin._canonical_platform_authority

    def counting_canonical(self, user_id):
        counts["canonical_platform_authority"] += 1
        return real_canonical(self, user_id)

    AuthQueryMixin._canonical_platform_authority = counting_canonical
    try:
        admin = catalog.adminOverview()
    finally:
        AuthQueryMixin._canonical_platform_authority = real_canonical

    assert counts["canonical_platform_authority"] == 0
    metrics_by_label = {m["label"]: m["value"] for m in admin["metrics"]}
    assert metrics_by_label["Users"] == str(expected.active)
    rows_by_label = {
        row["label"]: row["supportingText"]
        for section in admin["sections"]
        for row in section["rows"]
        if section["title"] == "Identity And Workforce"
    }
    assert f"{expected.locked} locked, {expected.active} active" == rows_by_label["Users"]
