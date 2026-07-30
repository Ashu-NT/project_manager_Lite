from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from src.core.platform.common.exceptions import (
    BusinessRuleError,
    ConcurrencyError,
)
from src.core.platform.infrastructure.persistence.orm.auth import UserORM
from src.core.platform.infrastructure.persistence.orm.tenant import TenantORM
from src.core.platform.infrastructure.persistence.repositories.auth import (
    SqlAlchemyUserRepository,
)
from src.core.platform.infrastructure.persistence.repositories.user_tenant import (
    SqlAlchemyUserTenantMembershipRepository,
)
from src.core.platform.tenancy import (
    MEMBERSHIP_STATUS_ACTIVE,
    MEMBERSHIP_STATUS_INVITED,
    MEMBERSHIP_STATUS_REMOVED,
    MEMBERSHIP_STATUS_SUSPENDED,
    UserTenantMembership,
)
from src.infra.persistence.migrations.runner import run_migrations


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATIONS_ROOT = (
    _REPO_ROOT / "src" / "infra" / "persistence" / "migrations"
)


def _alembic_config(database_url: str) -> Config:
    config = Config(str(_MIGRATIONS_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_MIGRATIONS_ROOT))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _seed_user_and_tenant(
    session,
    *,
    user_id: str,
    tenant_id: str,
    username: str,
) -> None:
    now = datetime.now(timezone.utc)
    session.add(
        UserORM(
            id=user_id,
            username=username,
            password_hash="x",
            is_active=True,
            created_at=now,
            updated_at=now,
            version=1,
            session_revision=1,
            mfa_enabled=False,
            failed_login_attempts=0,
            must_change_password=False,
        )
    )
    session.add(
        TenantORM(
            id=tenant_id,
            tenant_code=tenant_id.upper(),
            display_name=tenant_id,
            is_active=True,
            version=1,
        )
    )
    session.flush()


def test_membership_domain_enforces_explicit_lifecycle_transitions() -> None:
    invited_at = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    membership = UserTenantMembership.invite(
        "user-1",
        "tenant-1",
        invited_by_user_id="admin-1",
        invited_at=invited_at,
        expires_at=invited_at + timedelta(days=2),
    )

    assert membership.status == MEMBERSHIP_STATUS_INVITED
    assert membership.is_active is False
    assert membership.invitation_is_expired(
        at=invited_at + timedelta(days=1)
    ) is False

    accepted = membership.accept_invitation(
        accepted_at=invited_at + timedelta(hours=1)
    )
    suspended = accepted.suspend(
        suspended_at=invited_at + timedelta(hours=2)
    )
    reactivated = suspended.reactivate(
        reactivated_at=invited_at + timedelta(hours=3)
    )
    removed = reactivated.remove(
        removed_at=invited_at + timedelta(hours=4)
    )

    assert accepted.status == MEMBERSHIP_STATUS_ACTIVE
    assert accepted.is_active is True
    assert suspended.status == MEMBERSHIP_STATUS_SUSPENDED
    assert suspended.is_active is False
    assert reactivated.status == MEMBERSHIP_STATUS_ACTIVE
    assert reactivated.suspended_at is None
    assert removed.status == MEMBERSHIP_STATUS_REMOVED
    assert removed.is_active is False
    assert membership.status == MEMBERSHIP_STATUS_INVITED


def test_expired_invitation_denies_acceptance_and_can_be_reinvited() -> None:
    invited_at = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    membership = UserTenantMembership.invite(
        "user-1",
        "tenant-1",
        invited_by_user_id="admin-1",
        invited_at=invited_at,
        expires_at=invited_at + timedelta(hours=1),
    )

    with pytest.raises(BusinessRuleError) as expired_error:
        membership.accept_invitation(
            accepted_at=invited_at + timedelta(hours=1)
        )

    revoked = membership.revoke_invitation(
        revoked_at=invited_at + timedelta(hours=2)
    )
    reinvited = revoked.reinvite(
        invited_by_user_id="admin-2",
        invited_at=invited_at + timedelta(hours=3),
        expires_at=invited_at + timedelta(days=1),
    )

    assert expired_error.value.code == (
        "USER_TENANT_MEMBERSHIP_INVITATION_EXPIRED"
    )
    assert revoked.status == MEMBERSHIP_STATUS_REMOVED
    assert revoked.revoked_at is not None
    assert reinvited.status == MEMBERSHIP_STATUS_INVITED
    assert reinvited.invited_by_user_id == "admin-2"
    assert reinvited.revoked_at is None
    assert reinvited.removed_at is None


def test_membership_repository_persists_lifecycle_and_rejects_stale_update(
    session,
) -> None:
    _seed_user_and_tenant(
        session,
        user_id="membership-user",
        tenant_id="membership-tenant",
        username="membership_user",
    )
    session.add(
        UserORM(
            id="membership-admin",
            username="membership_admin",
            password_hash="x",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            version=1,
            session_revision=1,
            mfa_enabled=False,
            failed_login_attempts=0,
            must_change_password=False,
        )
    )
    session.flush()
    repository = SqlAlchemyUserTenantMembershipRepository(session)
    user_repository = SqlAlchemyUserRepository(session)
    invited_at = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    membership = UserTenantMembership.invite(
        "membership-user",
        "membership-tenant",
        invited_by_user_id="membership-admin",
        invited_at=invited_at,
        expires_at=invited_at + timedelta(days=2),
    )
    repository.add(membership)
    session.flush()

    assert repository.is_active_member(
        "membership-user",
        "membership-tenant",
    ) is False

    accepted = membership.accept_invitation(
        accepted_at=invited_at + timedelta(hours=1)
    )
    repository.update(accepted)
    session.flush()

    assert accepted.version == 2
    assert repository.is_active_member(
        "membership-user",
        "membership-tenant",
    ) is True
    assert [
        user.id
        for user in user_repository.list_for_tenant("membership-tenant")
    ] == ["membership-user"]

    current = repository.get("membership-user", "membership-tenant")
    stale = repository.get("membership-user", "membership-tenant")
    assert current is not None
    assert stale is not None
    repository.update(
        current.suspend(suspended_at=invited_at + timedelta(hours=2))
    )
    assert user_repository.list_for_tenant("membership-tenant") == []

    with pytest.raises(ConcurrencyError) as stale_error:
        repository.update(
            stale.remove(removed_at=invited_at + timedelta(hours=3))
        )

    assert stale_error.value.code == "STALE_WRITE"


def test_membership_lifecycle_migration_builds_production_shape(tmp_path) -> None:
    database_path = tmp_path / "membership-lifecycle.db"
    database_url = f"sqlite:///{database_path.as_posix()}"

    run_migrations(database_url)

    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            columns = {
                column["name"]
                for column in inspector.get_columns("user_tenants")
            }
            checks = {
                constraint["name"]
                for constraint in inspector.get_check_constraints(
                    "user_tenants"
                )
            }
            indexes = {
                index["name"]
                for index in inspector.get_indexes("user_tenants")
            }
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        engine.dispose()

    assert revision == "6f1a9c2e8d4b"
    assert {
        "status",
        "invited_by_user_id",
        "invitation_expires_at",
        "accepted_at",
        "suspended_at",
        "revoked_at",
        "removed_at",
        "version",
    } <= columns
    assert {
        "ck_user_tenants_status",
        "ck_user_tenants_active_status",
        "ck_user_tenants_version_positive",
    } <= checks
    assert {
        "idx_user_tenants_status",
        "idx_user_tenants_invitation_expiry",
    } <= indexes


def test_membership_lifecycle_migration_backfills_and_round_trips(
    tmp_path,
) -> None:
    database_path = tmp_path / "membership-lifecycle-backfill.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)
    command.upgrade(config, "b5c6d7e8f9a0")

    engine = create_engine(database_url, future=True)
    legacy_time = "2026-07-30 08:00:00"
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, username, password_hash, is_active, created_at, "
                    "updated_at, version) VALUES "
                    "('migration-active-user', 'migration_active', 'x', 1, "
                    ":stamp, :stamp, 1), "
                    "('migration-inactive-user', 'migration_inactive', 'x', 1, "
                    ":stamp, :stamp, 1)"
                ),
                {"stamp": legacy_time},
            )
            connection.execute(
                text(
                    "INSERT INTO tenants "
                    "(id, tenant_code, display_name, tenant_status, "
                    "is_active, version) VALUES "
                    "('migration-tenant', 'MIGRATION', 'Migration', "
                    "'active', 1, 1)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO user_tenants "
                    "(id, user_id, tenant_id, is_active, tenant_role, "
                    "invited_at, joined_at, created_at, updated_at) VALUES "
                    "('membership-active', 'migration-active-user', "
                    "'migration-tenant', 1, 'member', NULL, :stamp, "
                    ":stamp, :stamp), "
                    "('membership-inactive', 'migration-inactive-user', "
                    "'migration-tenant', 0, 'member', NULL, :stamp, "
                    ":stamp, :stamp)"
                ),
                {"stamp": legacy_time},
            )
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT id, status, is_active, accepted_at, "
                    "suspended_at, version FROM user_tenants ORDER BY id"
                )
            ).mappings().all()
    finally:
        engine.dispose()

    rows_by_id = {row["id"]: row for row in rows}
    assert rows_by_id["membership-active"]["status"] == "active"
    assert rows_by_id["membership-active"]["is_active"] == 1
    assert rows_by_id["membership-active"]["accepted_at"] is not None
    assert rows_by_id["membership-active"]["suspended_at"] is None
    assert rows_by_id["membership-inactive"]["status"] == "suspended"
    assert rows_by_id["membership-inactive"]["is_active"] == 0
    assert rows_by_id["membership-inactive"]["accepted_at"] is not None
    assert rows_by_id["membership-inactive"]["suspended_at"] is not None
    assert rows_by_id["membership-inactive"]["version"] == 1

    command.downgrade(config, "b5c6d7e8f9a0")
    engine = create_engine(database_url, future=True)
    try:
        downgraded_columns = {
            column["name"]
            for column in inspect(engine).get_columns("user_tenants")
        }
    finally:
        engine.dispose()
    assert "status" not in downgraded_columns
    assert "version" not in downgraded_columns

    command.upgrade(config, "head")
