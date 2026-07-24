"""Migration D: Backfill security/compliance records from audit_logs → audit_entries.

Revision ID: v7w8x9y0z1a2
Revises: u6v7w8x9y0z1
Create Date: 2026-06-14

Copies auth.*, approval.*, and other compliance records from audit_logs into
audit_entries with proper operation, severity, and compliance_tag mappings.

Batched at 1000 rows to avoid locking on large datasets.
"""

from __future__ import annotations

import logging

from alembic import op
import sqlalchemy as sa

revision = "v7w8x9y0z1a2"
down_revision = "u6v7w8x9y0z1"
branch_labels = None
depends_on = None

logger = logging.getLogger(__name__)

_ACTION_TO_OPERATION = {
    "auth.login": ("login", "high", "SOC2"),
    "auth.logout": ("logout", "low", "SOC2"),
    "auth.failed_login": ("failed_login", "high", "SOC2"),
    "approval.grant": ("update", "medium", "none"),
    "approval.reject": ("update", "medium", "none"),
    "approval.request": ("create", "low", "none"),
    "user.create": ("create", "medium", "SOC2"),
    "user.update": ("update", "medium", "SOC2"),
    "user.deactivate": ("update", "medium", "SOC2"),
    "role.create": ("create", "medium", "SOC2"),
    "role.update": ("update", "medium", "SOC2"),
    "role.delete": ("delete", "medium", "SOC2"),
    "role.permission.add": ("permission_change", "medium", "SOC2"),
    "role.permission.remove": ("permission_change", "medium", "SOC2"),
    "user.role.assign": ("permission_change", "medium", "SOC2"),
    "user.role.revoke": ("permission_change", "medium", "SOC2"),
    "module_entitlement.grant": ("update", "medium", "none"),
    "module_entitlement.revoke": ("update", "medium", "none"),
    "access_scope.grant": ("permission_change", "medium", "none"),
    "access_scope.revoke": ("delete", "medium", "none"),
}

_SECURITY_ACTIONS = tuple(_ACTION_TO_OPERATION)


def _is_sqlite_lock_error(exc: sa.exc.OperationalError) -> bool:
    message = str(getattr(exc, "orig", exc) or "").lower()
    return "database table is locked" in message or "database is locked" in message


def _best_effort_wal_checkpoint(conn) -> None:
    try:
        conn.execute(sa.text("PRAGMA wal_checkpoint"))
    except sa.exc.OperationalError as exc:
        if not _is_sqlite_lock_error(exc):
            raise
        logger.warning(
            "Skipping SQLite WAL checkpoint for migration %s because the database is busy.",
            revision,
        )


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "audit_logs" not in inspector.get_table_names():
        return

    offset = 0
    batch_size = 1000
    security_placeholders = ", ".join(f"'{a}'" for a in sorted(_SECURITY_ACTIONS))

    while True:
        rows = conn.execute(
            sa.text(
                f"""
                SELECT id, action, entity_type, entity_id, actor_user_id,
                       actor_username, organization_id, tenant_id, occurred_at,
                       details_json
                FROM audit_logs
                WHERE action IN ({security_placeholders})
                ORDER BY occurred_at
                LIMIT :batch_size OFFSET :offset
                """
            ),
            {"batch_size": batch_size, "offset": offset},
        ).fetchall()

        if not rows:
            break

        for row in rows:
            action = row[1] or ""
            op_tuple = _ACTION_TO_OPERATION.get(action, ("access", "low", "none"))
            operation, severity, compliance_tag = op_tuple
            conn.execute(
                sa.text(
                    """
                    INSERT OR IGNORE INTO audit_entries
                        (id, timestamp, actor_id, actor_type, actor_username,
                         entity_type, entity_id, operation, module,
                         tenant_id, organization_id, source, severity,
                         compliance_tag, metadata_json)
                    VALUES
                        (:id, :timestamp, :actor_id, 'user', :actor_username,
                         :entity_type, :entity_id, :operation, 'platform',
                         :tenant_id, :organization_id, 'api', :severity,
                         :compliance_tag, :metadata_json)
                    """
                ),
                {
                    "id": row[0],
                    "timestamp": row[8],
                    "actor_id": row[4],
                    "actor_username": row[5],
                    "entity_type": row[2] or "auth_session",
                    "entity_id": row[3] or row[0],
                    "operation": operation,
                    "tenant_id": row[7],
                    "organization_id": row[6],
                    "severity": severity,
                    "compliance_tag": compliance_tag,
                    "metadata_json": row[9] or "{}",
                },
            )

        offset += batch_size

    _best_effort_wal_checkpoint(conn)


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "audit_logs" not in inspector.get_table_names():
        return
    conn.execute(sa.text("DELETE FROM audit_entries WHERE id IN (SELECT id FROM audit_logs)"))
