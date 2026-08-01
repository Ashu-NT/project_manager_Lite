"""Read-only, schema-aware inventory for tenancy and authorization migration."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection


_MEMBERSHIP_LIFECYCLE_COLUMNS = frozenset(
    {
        "status",
        "invited_by_user_id",
        "invited_at",
        "invitation_expires_at",
        "invitation_token_hash",
        "accepted_at",
        "suspended_at",
        "revoked_at",
        "removed_at",
        "version",
    }
)
_SECURITY_TABLES = (
    "users",
    "tenants",
    "organizations",
    "roles",
    "user_tenants",
    "role_bindings",
    "role_delegation_policies",
    "role_permissions",
    "auth_sessions",
    "audit_entries",
    "platform_events",
)


def _is_true(value: object) -> bool:
    return value is True or value == 1 or str(value or "").strip().lower() in {
        "true",
        "yes",
    }


class _SchemaReader:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.inspector = inspect(connection)
        self.tables = frozenset(self.inspector.get_table_names())
        self._columns: dict[str, frozenset[str]] = {}

    def columns(self, table_name: str) -> frozenset[str]:
        if table_name not in self.tables:
            return frozenset()
        if table_name not in self._columns:
            self._columns[table_name] = frozenset(
                str(column["name"])
                for column in self.inspector.get_columns(table_name)
            )
        return self._columns[table_name]

    def rows(
        self,
        table_name: str,
        requested_columns: tuple[str, ...],
    ) -> list[dict[str, Any]]:
        available = self.columns(table_name)
        selected = tuple(column for column in requested_columns if column in available)
        if not selected:
            return []
        quote = self.connection.dialect.identifier_preparer.quote
        statement = (
            f"SELECT {', '.join(quote(column) for column in selected)} "
            f"FROM {quote(table_name)}"
        )
        rows = self.connection.execute(text(statement)).mappings().all()
        return [dict(row) for row in rows]

    def count(self, table_name: str) -> int | None:
        if table_name not in self.tables:
            return None
        quote = self.connection.dialect.identifier_preparer.quote
        return int(
            self.connection.execute(
                text(f"SELECT COUNT(*) FROM {quote(table_name)}")
            ).scalar_one()
        )


def _stable_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: json.dumps(record, sort_keys=True, default=str),
    )


def _append_finding(
    findings: list[dict[str, Any]],
    *,
    code: str,
    severity: str,
    summary: str,
    records: list[dict[str, Any]],
) -> None:
    if not records:
        return
    findings.append(
        {
            "code": code,
            "severity": severity,
            "summary": summary,
            "count": len(records),
            "records": _stable_records(records),
        }
    )


def _database_revisions(reader: _SchemaReader) -> list[str]:
    rows = reader.rows("alembic_version", ("version_num",))
    return sorted(str(row.get("version_num") or "") for row in rows)


def _schema_snapshot(reader: _SchemaReader) -> dict[str, Any]:
    roles_columns = reader.columns("roles")
    binding_indexes = (
        {
            str(index["name"])
            for index in reader.inspector.get_indexes("role_bindings")
            if index.get("name")
        }
        if "role_bindings" in reader.tables
        else set()
    )
    role_uniques = (
        [
            {
                "name": constraint.get("name"),
                "columns": sorted(constraint.get("column_names") or ()),
            }
            for constraint in reader.inspector.get_unique_constraints("roles")
        ]
        if "roles" in reader.tables
        else []
    )
    return {
        "table_counts": {
            table_name: reader.count(table_name)
            for table_name in _SECURITY_TABLES
        },
        "capabilities": {
            "membership_lifecycle": sorted(
                reader.columns("user_tenants")
                & _MEMBERSHIP_LIFECYCLE_COLUMNS
            ),
            "membership_lifecycle_complete": (
                _MEMBERSHIP_LIFECYCLE_COLUMNS
                <= reader.columns("user_tenants")
            ),
            "role_metadata": sorted(
                roles_columns
                & {
                    "tenant_id",
                    "display_name",
                    "allowed_scope_type",
                    "is_assignable",
                    "status",
                    "policy_version",
                    "created_at",
                    "updated_at",
                }
            ),
            "canonical_role_bindings": "role_bindings" in reader.tables,
            "canonical_active_unique_indexes": sorted(
                binding_indexes
                & {
                    "ux_role_bindings_active_platform",
                    "ux_role_bindings_active_tenant",
                    "ux_role_bindings_active_resource",
                }
            ),
            "role_unique_constraints": sorted(
                role_uniques,
                key=lambda item: str(item.get("name") or ""),
            ),
        },
    }


def _inventory_data(
    reader: _SchemaReader,
    findings: list[dict[str, Any]],
) -> dict[str, Any]:
    membership_rows = reader.rows(
        "user_tenants",
        (
            "id",
            "user_id",
            "tenant_id",
            "status",
            "is_active",
            "tenant_role",
        ),
    )
    active_tenants_by_user: dict[str, set[str]] = defaultdict(set)
    duplicated_membership_authority: list[dict[str, Any]] = []
    for row in membership_rows:
        user_id = str(row.get("user_id") or "").strip()
        tenant_id = str(row.get("tenant_id") or "").strip()
        if not user_id or not tenant_id:
            continue
        membership_status = str(row.get("status") or "").strip().lower()
        status_allows_access = (
            not membership_status or membership_status == "active"
        )
        if _is_true(row.get("is_active")) and status_allows_access:
            active_tenants_by_user[user_id].add(tenant_id)
        tenant_role = str(row.get("tenant_role") or "member").strip().lower()
        if tenant_role and tenant_role != "member":
            duplicated_membership_authority.append(
                {
                    "membership_id": row.get("id"),
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "tenant_role": tenant_role,
                }
            )

    canonical_rows = reader.rows(
        "role_bindings",
        (
            "id",
            "principal_id",
            "role_id",
            "tenant_id",
            "actual_scope_type",
            "actual_scope_id",
            "expires_at",
            "revoked_at",
        ),
    )
    canonical_without_membership: list[dict[str, Any]] = []
    expired_unrevoked: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    for row in canonical_rows:
        tenant_id = str(row.get("tenant_id") or "").strip() or None
        principal_id = str(row.get("principal_id") or "").strip()
        scope_type = str(row.get("actual_scope_type") or "").strip().lower()
        if (
            tenant_id is not None
            and tenant_id not in active_tenants_by_user.get(principal_id, set())
        ):
            canonical_without_membership.append(
                {
                    "binding_id": row.get("id"),
                    "principal_id": principal_id,
                    "tenant_id": tenant_id,
                    "actual_scope_type": scope_type,
                    "actual_scope_id": row.get("actual_scope_id"),
                }
            )
        expires_at = row.get("expires_at")
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                expires_at = None
        if isinstance(expires_at, datetime):
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= now and row.get("revoked_at") is None:
                expired_unrevoked.append(
                    {
                        "binding_id": row.get("id"),
                        "principal_id": principal_id,
                        "tenant_id": tenant_id,
                    }
                )

    _append_finding(
        findings,
        code="MEMBERSHIP_ROLE_AUTHORITY_PRESENT",
        severity="medium",
        summary="Membership tenant_role still duplicates authorization authority.",
        records=duplicated_membership_authority,
    )
    _append_finding(
        findings,
        code="CANONICAL_BINDING_WITHOUT_ACTIVE_MEMBERSHIP",
        severity="critical",
        summary="A customer canonical binding lacks active tenant membership.",
        records=canonical_without_membership,
    )
    _append_finding(
        findings,
        code="CANONICAL_BINDING_EXPIRED_NOT_REVOKED",
        severity="medium",
        summary="An expired unrevoked binding can block reassignment under current indexes.",
        records=expired_unrevoked,
    )

    return {
        "active_membership_counts_by_user": {
            user_id: len(tenant_ids)
            for user_id, tenant_ids in sorted(active_tenants_by_user.items())
        },
    }


def _append_schema_findings(
    reader: _SchemaReader,
    schema: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    required_role_columns = {
        "tenant_id",
        "display_name",
        "allowed_scope_type",
        "is_assignable",
        "status",
        "policy_version",
        "created_at",
        "updated_at",
    }
    missing_role_columns = sorted(required_role_columns - reader.columns("roles"))
    if "role_bindings" not in reader.tables or missing_role_columns:
        _append_finding(
            findings,
            code="CANONICAL_AUTHORIZATION_SCHEMA_INCOMPLETE",
            severity="high",
            summary="Canonical role metadata or role_bindings is not fully deployed.",
            records=[
                {
                    "role_bindings_present": "role_bindings" in reader.tables,
                    "missing_role_columns": missing_role_columns,
                }
            ],
        )
    missing_membership_columns = sorted(
        _MEMBERSHIP_LIFECYCLE_COLUMNS - reader.columns("user_tenants")
    )
    if "user_tenants" in reader.tables and missing_membership_columns:
        _append_finding(
            findings,
            code="MEMBERSHIP_LIFECYCLE_SCHEMA_MISSING",
            severity="high",
            summary="Membership lifecycle state, invitation, and version fields are incomplete.",
            records=[
                {
                    "table": "user_tenants",
                    "missing_columns": missing_membership_columns,
                }
            ],
        )


def build_tenancy_rbac_inventory(connection: Connection) -> dict[str, Any]:
    """Build a deterministic security inventory without mutating the database."""

    reader = _SchemaReader(connection)
    schema = _schema_snapshot(reader)
    findings: list[dict[str, Any]] = []
    _append_schema_findings(reader, schema, findings)
    data = _inventory_data(reader, findings)
    findings.sort(key=lambda finding: (finding["severity"], finding["code"]))
    severity_counts = Counter(finding["severity"] for finding in findings)
    snapshot = {
        "database": {
            "dialect": connection.dialect.name,
            "alembic_revisions": _database_revisions(reader),
        },
        "schema": schema,
        "data": data,
        "findings": findings,
        "finding_counts_by_severity": dict(sorted(severity_counts.items())),
    }
    canonical_snapshot = json.dumps(
        snapshot,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "snapshot_sha256": hashlib.sha256(
            canonical_snapshot.encode("utf-8")
        ).hexdigest(),
        "snapshot": snapshot,
    }


__all__ = ["build_tenancy_rbac_inventory"]
