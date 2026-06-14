"""Migration C: Backfill business-operation records from audit_logs → activity_entries.

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-06-14

Copies all non-security audit_logs records into activity_entries. Security and
compliance records (auth.*, approval.*, user.*, role.*, access_scope.*,
module_entitlement.*) are excluded — they are handled by Migration D.

Batched at 1000 rows to avoid locking on large datasets.
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "u6v7w8x9y0z1"
down_revision = "t5u6v7w8x9y0"
branch_labels = None
depends_on = None

_SECURITY_ACTIONS = {
    "auth.login",
    "auth.logout",
    "auth.failed_login",
    "approval.grant",
    "approval.reject",
    "approval.request",
    "user.create",
    "user.update",
    "user.deactivate",
    "role.create",
    "role.update",
    "role.delete",
    "role.permission.add",
    "role.permission.remove",
    "user.role.assign",
    "user.role.revoke",
    "module_entitlement.grant",
    "module_entitlement.revoke",
    "access_scope.grant",
    "access_scope.revoke",
}

_ENTITY_TYPE_MODULE_MAP = {
    "task": "project_management",
    "task_assignment": "project_management",
    "task_dependency": "project_management",
    "project": "project_management",
    "resource": "project_management",
    "cost_item": "project_management",
    "project_baseline": "project_management",
    "risk_register": "project_management",
    "inventory_item": "inventory_procurement",
    "inventory_item_category": "inventory_procurement",
    "stock_item": "inventory_procurement",
    "stock_reservation": "inventory_procurement",
    "purchase_requisition": "inventory_procurement",
    "purchase_order": "inventory_procurement",
}


def _derive_module(entity_type: str, action: str) -> str:
    if entity_type in _ENTITY_TYPE_MODULE_MAP:
        return _ENTITY_TYPE_MODULE_MAP[entity_type]
    for prefix, module in (
        ("task", "project_management"),
        ("project", "project_management"),
        ("resource", "project_management"),
        ("cost", "project_management"),
        ("risk", "project_management"),
        ("baseline", "project_management"),
        ("portfolio", "project_management"),
        ("inventory", "inventory_procurement"),
        ("stock", "inventory_procurement"),
        ("purchase", "inventory_procurement"),
    ):
        if entity_type.startswith(prefix) or action.startswith(prefix):
            return module
    return "platform"


def upgrade() -> None:
    conn = op.get_bind()

    # Check audit_logs exists before proceeding
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
                       organization_id, tenant_id, occurred_at, details_json
                FROM audit_logs
                WHERE action NOT IN ({security_placeholders})
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
            entity_type = row[2] or ""
            module = _derive_module(entity_type, action)
            details_json = row[8] or "{}"
            try:
                details = json.loads(details_json)
            except (ValueError, TypeError):
                details = {}
            context = {}
            if row[5]:
                context["organization_id"] = row[5]
            conn.execute(
                sa.text(
                    """
                    INSERT OR IGNORE INTO activity_entries
                        (id, action, entity_type, entity_id, actor_id, module,
                         tenant_id, organization_id, timestamp, type,
                         human_message, details_json, context_json,
                         visibility)
                    VALUES
                        (:id, :action, :entity_type, :entity_id, :actor_id,
                         :module, :tenant_id, :organization_id, :timestamp,
                         'info', :human_message, :details_json, :context_json,
                         'workspace')
                    """
                ),
                {
                    "id": row[0],
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": row[3] or "",
                    "actor_id": row[4],
                    "module": module,
                    "tenant_id": row[6],
                    "organization_id": row[5],
                    "timestamp": row[7],
                    "human_message": action,
                    "details_json": json.dumps(details),
                    "context_json": json.dumps(context),
                },
            )

        offset += batch_size

    conn.execute(sa.text("PRAGMA wal_checkpoint"))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if "audit_logs" not in inspector.get_table_names():
        return
    conn.execute(sa.text("DELETE FROM activity_entries WHERE id IN (SELECT id FROM audit_logs)"))
