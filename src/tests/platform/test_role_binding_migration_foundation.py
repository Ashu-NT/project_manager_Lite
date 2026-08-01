from __future__ import annotations

# RBAC-TRANSITION-ONLY: Remove after CANONICAL_ONLY and migration retention.

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from src.core.platform.auth.domain import (
    LEGACY_BINDING_MIGRATION_QUARANTINED,
    LEGACY_BINDING_MIGRATION_READY,
    AuthorizationMigrationBatch,
    LegacyRoleBindingMigrationRecord,
    legacy_role_binding_snapshot_sha256,
)
from src.core.platform.common.exceptions import ValidationError
from src.core.platform.infrastructure.persistence.orm.auth import (
    AuthorizationMigrationBatchORM,
    LegacyRoleBindingMigrationRecordORM,
)
from src.infra.composition.repositories import build_repository_bundle
from src.infra.persistence.migrations.runner import run_migrations


_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATIONS_ROOT = (
    _REPO_ROOT / "src" / "infra" / "persistence" / "migrations"
)
_INVENTORY_HASH = "a" * 64


def _alembic_config(database_url: str) -> Config:
    config = Config(str(_MIGRATIONS_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(_MIGRATIONS_ROOT))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _record(
    *,
    batch_id: str = "migration-batch",
    status: str = LEGACY_BINDING_MIGRATION_QUARANTINED,
    quarantine_reason_code: str | None = "AMBIGUOUS_TENANT",
    resolved_tenant_id: str | None = None,
    resolved_scope_type: str | None = None,
    reviewed_by: str | None = None,
    reviewed_at: datetime | None = None,
) -> LegacyRoleBindingMigrationRecord:
    now = reviewed_at or datetime.now(timezone.utc)
    legacy_binding_id = "legacy-binding"
    user_id = "source-user"
    role_id = "source-role"
    return LegacyRoleBindingMigrationRecord(
        id="migration-record",
        batch_id=batch_id,
        legacy_binding_id=legacy_binding_id,
        source_user_id=user_id,
        source_role_id=role_id,
        source_organization_id=None,
        source_snapshot_sha256=legacy_role_binding_snapshot_sha256(
            legacy_binding_id=legacy_binding_id,
            user_id=user_id,
            role_id=role_id,
            organization_id=None,
        ),
        status=status,
        quarantine_reason_code=quarantine_reason_code,
        resolved_tenant_id=resolved_tenant_id,
        resolved_scope_type=resolved_scope_type,
        resolved_scope_id=None,
        canonical_binding_id=None,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        created_at=now,
        updated_at=now,
    )


def test_quarantine_record_preserves_exact_source_snapshot() -> None:
    record = _record()

    assert record.status == LEGACY_BINDING_MIGRATION_QUARANTINED
    assert record.quarantine_reason_code == "AMBIGUOUS_TENANT"
    assert record.resolved_tenant_id is None
    assert record.canonical_binding_id is None

    with pytest.raises(ValidationError) as exc_info:
        replace(record, source_user_id="tampered-user")
    assert exc_info.value.code == "AUTH_MIGRATION_SOURCE_HASH_MISMATCH"


def test_ready_record_requires_reviewed_tenant_scope() -> None:
    reviewed_at = datetime.now(timezone.utc)
    record = _record(
        status=LEGACY_BINDING_MIGRATION_READY,
        quarantine_reason_code=None,
        resolved_tenant_id="tenant-a",
        resolved_scope_type="tenant",
        reviewed_by="security-reviewer",
        reviewed_at=reviewed_at,
    )

    assert record.resolved_tenant_id == "tenant-a"
    assert record.reviewed_by == "security-reviewer"

    with pytest.raises(ValidationError) as exc_info:
        _record(
            status=LEGACY_BINDING_MIGRATION_READY,
            quarantine_reason_code=None,
            resolved_tenant_id="tenant-a",
            resolved_scope_type="tenant",
        )
    assert exc_info.value.code == "AUTH_MIGRATION_REVIEW_REQUIRED"


def test_migration_repository_persists_batch_and_quarantine(session) -> None:
    repositories = build_repository_bundle(session)
    reviewed_at = datetime.now(timezone.utc)
    batch = AuthorizationMigrationBatch.create(
        source_inventory_sha256=_INVENTORY_HASH,
        source_record_count=1,
        reviewed_plan_sha256="c" * 64,
        reviewer_id="security-reviewer",
        reviewed_at=reviewed_at,
        created_by="migration-operator",
    )
    record = _record(batch_id=batch.id)

    repositories.role_binding_migration_repo.add_batch(batch)
    repositories.role_binding_migration_repo.add_record(record)
    session.commit()

    assert repositories.role_binding_migration_repo.get_batch(batch.id) == batch
    assert repositories.role_binding_migration_repo.list_records(batch.id) == [
        record
    ]
    persisted_batch = session.get(AuthorizationMigrationBatchORM, batch.id)
    assert persisted_batch is not None
    session.delete(persisted_batch)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_database_rejects_unreviewed_ready_record(session) -> None:
    repositories = build_repository_bundle(session)
    reviewed_at = datetime.now(timezone.utc)
    batch = AuthorizationMigrationBatch.create(
        source_inventory_sha256=_INVENTORY_HASH,
        source_record_count=1,
        reviewed_plan_sha256="c" * 64,
        reviewer_id="security-reviewer",
        reviewed_at=reviewed_at,
        created_by="migration-operator",
    )
    repositories.role_binding_migration_repo.add_batch(batch)
    session.flush()
    now = datetime.now(timezone.utc)
    session.add(
        LegacyRoleBindingMigrationRecordORM(
            id="unsafe-ready-record",
            batch_id=batch.id,
            legacy_binding_id="legacy-binding",
            source_user_id="source-user",
            source_role_id="source-role",
            source_organization_id=None,
            source_snapshot_sha256="b" * 64,
            status=LEGACY_BINDING_MIGRATION_READY,
            quarantine_reason_code=None,
            resolved_tenant_id="tenant-a",
            resolved_scope_type="tenant",
            resolved_scope_id=None,
            canonical_binding_id=None,
            reviewed_by=None,
            reviewed_at=None,
            created_at=now,
            updated_at=now,
            version=1,
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_migration_revision_builds_and_round_trips_foundation(tmp_path) -> None:
    database_path = tmp_path / "role-binding-migration.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    run_migrations(database_url)

    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            assert inspector.has_table("authorization_migration_batches")
            assert inspector.has_table(
                "legacy_role_binding_migration_records"
            )
            record_checks = {
                constraint["name"]
                for constraint in inspector.get_check_constraints(
                    "legacy_role_binding_migration_records"
                )
            }
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
    finally:
        engine.dispose()
    assert revision == "b1n2o3t4i5f6"
    assert {
        "ck_legacy_role_binding_migration_canonical_state",
        "ck_legacy_role_binding_migration_resolution",
        "ck_legacy_role_binding_migration_review",
        "ck_legacy_role_binding_migration_scope_shape",
    } <= record_checks

    config = _alembic_config(database_url)
    command.downgrade(config, "8b3c4d5e6f7a")
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as connection:
            inspector = inspect(connection)
            assert not inspector.has_table(
                "legacy_role_binding_migration_records"
            )
            assert not inspector.has_table("authorization_migration_batches")
    finally:
        engine.dispose()

    command.upgrade(config, "head")
