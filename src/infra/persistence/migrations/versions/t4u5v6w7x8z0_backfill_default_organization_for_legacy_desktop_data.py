"""Backfill legacy desktop tenant data into the DEFAULT organization.

Revision ID: t4u5v6w7x8z0
Revises: t4u5v6w7x8y9
Create Date: 2026-06-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "t4u5v6w7x8z0"
down_revision = "t4u5v6w7x8y9"
branch_labels = None
depends_on = None

_DIRECT_DEFAULT_TABLES = (
    "approval_requests",
    "audit_logs",
    "portfolio_intake_items",
    "portfolio_scenarios",
    "portfolio_scoring_templates",
    "projects",
    "resources",
)


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def _ensure_default_organization(connection: sa.Connection, inspector: sa.Inspector) -> str | None:
    if not _table_exists(inspector, "organizations"):
        return None
    row = connection.execute(
        sa.text(
            "SELECT id "
            "FROM organizations "
            "WHERE organization_code = 'DEFAULT' "
            "ORDER BY display_name ASC, id ASC "
            "LIMIT 1"
        )
    ).first()
    if row is not None and row[0]:
        return str(row[0])
    fallback = connection.execute(
        sa.text(
            "SELECT id "
            "FROM organizations "
            "ORDER BY is_active DESC, display_name ASC, id ASC "
            "LIMIT 1"
        )
    ).first()
    return str(fallback[0]) if fallback is not None and fallback[0] else None


def _activate_default_organization(connection: sa.Connection, default_org_id: str) -> None:
    connection.execute(
        sa.text(
            "UPDATE organizations "
            "SET is_active = CASE WHEN id = :organization_id THEN 1 ELSE 0 END"
        ),
        {"organization_id": default_org_id},
    )


def _collapse_table_to_default(
    connection: sa.Connection,
    inspector: sa.Inspector,
    table_name: str,
    default_org_id: str,
) -> None:
    if "organization_id" not in _column_names(inspector, table_name):
        return
    connection.execute(
        sa.text(
            f"""
            UPDATE {table_name}
               SET organization_id = :organization_id
             WHERE organization_id IS NULL
                OR organization_id = ''
                OR organization_id <> :organization_id
            """
        ),
        {"organization_id": default_org_id},
    )


def _merge_default_module_entitlements(
    connection: sa.Connection,
    inspector: sa.Inspector,
    default_org_id: str,
) -> None:
    table_name = "organization_module_entitlements"
    required_columns = {
        "organization_id",
        "module_code",
        "licensed",
        "enabled",
        "updated_at",
    }
    if not _table_exists(inspector, table_name):
        return
    if not required_columns.issubset(_column_names(inspector, table_name)):
        return
    rows = connection.execute(
        sa.text(
            f"""
            SELECT
                module_code,
                MAX(CASE WHEN licensed THEN 1 ELSE 0 END) AS licensed,
                MAX(CASE WHEN enabled THEN 1 ELSE 0 END) AS enabled,
                MAX(updated_at) AS updated_at
            FROM {table_name}
            GROUP BY module_code
            """
        )
    ).mappings().all()
    has_lifecycle_status = "lifecycle_status" in _column_names(inspector, table_name)
    for row in rows:
        module_code = str(row["module_code"] or "").strip()
        if not module_code:
            continue
        licensed = int(row["licensed"] or 0)
        enabled = int(row["enabled"] or 0)
        lifecycle_status = "active" if enabled else ("licensed" if licensed else "inactive")
        updated_at = row["updated_at"]
        existing = connection.execute(
            sa.text(
                f"""
                SELECT 1
                  FROM {table_name}
                 WHERE organization_id = :organization_id
                   AND module_code = :module_code
                """
            ),
            {
                "organization_id": default_org_id,
                "module_code": module_code,
            },
        ).first()
        params = {
            "organization_id": default_org_id,
            "module_code": module_code,
            "licensed": licensed,
            "enabled": enabled,
            "updated_at": updated_at,
            "lifecycle_status": lifecycle_status,
        }
        if existing is None:
            if has_lifecycle_status:
                connection.execute(
                    sa.text(
                        f"""
                        INSERT INTO {table_name}
                            (organization_id, module_code, licensed, enabled, updated_at, lifecycle_status)
                        VALUES
                            (:organization_id, :module_code, :licensed, :enabled, :updated_at, :lifecycle_status)
                        """
                    ),
                    params,
                )
            else:
                connection.execute(
                    sa.text(
                        f"""
                        INSERT INTO {table_name}
                            (organization_id, module_code, licensed, enabled, updated_at)
                        VALUES
                            (:organization_id, :module_code, :licensed, :enabled, :updated_at)
                        """
                    ),
                    params,
                )
            continue
        if has_lifecycle_status:
            connection.execute(
                sa.text(
                    f"""
                    UPDATE {table_name}
                       SET licensed = :licensed,
                           enabled = :enabled,
                           updated_at = :updated_at,
                           lifecycle_status = :lifecycle_status
                     WHERE organization_id = :organization_id
                       AND module_code = :module_code
                    """
                ),
                params,
            )
        else:
            connection.execute(
                sa.text(
                    f"""
                    UPDATE {table_name}
                       SET licensed = :licensed,
                           enabled = :enabled,
                           updated_at = :updated_at
                     WHERE organization_id = :organization_id
                       AND module_code = :module_code
                    """
                ),
                params,
            )


def _move_non_conflicting_codes_to_default(
    connection: sa.Connection,
    inspector: sa.Inspector,
    *,
    table_name: str,
    code_column: str,
    default_org_id: str,
) -> None:
    if not _table_exists(inspector, table_name):
        return
    columns = _column_names(inspector, table_name)
    if {"id", "organization_id", code_column}.difference(columns):
        return
    existing_codes = {
        str(row[0]).strip()
        for row in connection.execute(
            sa.text(
                f"""
                SELECT {code_column}
                  FROM {table_name}
                 WHERE organization_id = :organization_id
                """
            ),
            {"organization_id": default_org_id},
        ).fetchall()
        if str(row[0] or "").strip()
    }
    rows = connection.execute(
        sa.text(
            f"""
            SELECT id, {code_column}
              FROM {table_name}
             WHERE organization_id IS NULL
                OR organization_id = ''
                OR organization_id <> :organization_id
            """
        ),
        {"organization_id": default_org_id},
    ).fetchall()
    for row_id, code in rows:
        normalized_code = str(code or "").strip()
        if not normalized_code or normalized_code in existing_codes:
            continue
        connection.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                   SET organization_id = :organization_id
                 WHERE id = :row_id
                """
            ),
            {
                "organization_id": default_org_id,
                "row_id": row_id,
            },
        )
        existing_codes.add(normalized_code)


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    default_org_id = _ensure_default_organization(connection, inspector)
    if not default_org_id:
        return

    _activate_default_organization(connection, default_org_id)
    inspector = sa.inspect(connection)

    _merge_default_module_entitlements(connection, inspector, default_org_id)

    for table_name in _DIRECT_DEFAULT_TABLES:
        _collapse_table_to_default(connection, inspector, table_name, default_org_id)

    _move_non_conflicting_codes_to_default(
        connection,
        inspector,
        table_name="platform_calendars",
        code_column="code",
        default_org_id=default_org_id,
    )
    _move_non_conflicting_codes_to_default(
        connection,
        inspector,
        table_name="shift_patterns",
        code_column="code",
        default_org_id=default_org_id,
    )


def downgrade() -> None:
    # Legacy tenant ownership collapse is not safely reversible.
    return
