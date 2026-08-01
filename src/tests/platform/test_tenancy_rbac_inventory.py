from __future__ import annotations

from sqlalchemy import create_engine

from src.infra.security import build_tenancy_rbac_inventory


def _seed_legacy_security_shape(connection) -> None:
    statements = (
        "CREATE TABLE alembic_version (version_num TEXT NOT NULL)",
        "INSERT INTO alembic_version VALUES ('legacy-head')",
        "CREATE TABLE users (id TEXT PRIMARY KEY, username TEXT NOT NULL)",
        "CREATE TABLE tenants (id TEXT PRIMARY KEY)",
        "CREATE TABLE organizations (id TEXT PRIMARY KEY, tenant_id TEXT)",
        "CREATE TABLE roles (id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE)",
        (
            "CREATE TABLE user_roles (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
            "role_id TEXT NOT NULL, organization_id TEXT)"
        ),
        (
            "CREATE TABLE user_tenants (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
            "tenant_id TEXT NOT NULL, is_active BOOLEAN NOT NULL, tenant_role TEXT NOT NULL)"
        ),
        (
            "CREATE TABLE scoped_access_grants (id TEXT PRIMARY KEY, tenant_id TEXT, "
            "scope_type TEXT NOT NULL, scope_id TEXT NOT NULL, user_id TEXT NOT NULL)"
        ),
        "INSERT INTO users VALUES ('u1', 'one'), ('u2', 'two'), ('u3', 'three')",
        "INSERT INTO tenants VALUES ('t1'), ('t2')",
        "INSERT INTO organizations VALUES ('o1', 't1'), ('o2', 't2')",
        "INSERT INTO roles VALUES ('r-admin', 'admin'), ('r-view', 'viewer'), ('r-org', 'org_admin')",
        (
            "INSERT INTO user_tenants VALUES "
            "('m1', 'u1', 't1', 1, 'member'), "
            "('m2', 'u2', 't2', 1, 'member')"
        ),
        (
            "INSERT INTO user_roles VALUES "
            "('ur1', 'u1', 'r-admin', NULL), "
            "('ur2', 'u2', 'r-view', 'o1'), "
            "('ur3', 'u3', 'r-org', NULL)"
        ),
        (
            "INSERT INTO scoped_access_grants VALUES "
            "('g1', 't1', 'organization', 'o2', 'u2'), "
            "('g2', NULL, 'organization', 'o1', 'u1'), "
            "('g3', 't1', 'organization', 'missing', 'u1')"
        ),
    )
    for statement in statements:
        connection.exec_driver_sql(statement)


def test_inventory_snapshot_hash_is_deterministic() -> None:
    engine = create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        _seed_legacy_security_shape(connection)
        first = build_tenancy_rbac_inventory(connection)
        second = build_tenancy_rbac_inventory(connection)

    assert first["snapshot_sha256"] == second["snapshot_sha256"]


def test_inventory_recognizes_complete_membership_lifecycle_schema(
    session,
) -> None:
    report = build_tenancy_rbac_inventory(session.connection())
    snapshot = report["snapshot"]
    finding_codes = {
        finding["code"] for finding in snapshot["findings"]
    }

    assert snapshot["schema"]["capabilities"][
        "membership_lifecycle_complete"
    ] is True
    assert "MEMBERSHIP_LIFECYCLE_SCHEMA_MISSING" not in finding_codes
