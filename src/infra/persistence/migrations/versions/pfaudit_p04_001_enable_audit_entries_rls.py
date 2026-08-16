"""Enable PostgreSQL row-level security on audit_entries (P0.4).

audit_entries has three legitimate write paths with different tenant
scoping (see SqlAlchemyAuditRepository): add()/add_for_tenant() write
tenant-scoped rows, while add_platform() deliberately writes rows with
tenant_id IS NULL for platform-level security events (login, tenant
provisioning, role governance, etc). The generic single-predicate
policy used for TENANT_RLS_TABLES would reject those NULL-tenant
inserts under WITH CHECK (NULL = current_setting(...) is never TRUE)
and would hide already-inserted NULL-tenant rows under USING, so
audit_entries needs its own policy that explicitly carries the
NULL-tenant case through instead of reusing that generic tuple.

Revision ID: pfaudit_p04_001
Revises: pfbill_e1_001
Create Date: 2026-08-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "pfaudit_p04_001"
down_revision = "pfbill_e1_001"
branch_labels = None
depends_on = None

_TABLE = "audit_entries"
_POLICY = "audit_entries_tenant_isolation_or_platform"
_PREDICATE = (
    "tenant_id = NULLIF(current_setting('app.tenant_id', true), '') "
    "OR tenant_id IS NULL"
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    existing = set(sa.inspect(bind).get_table_names())
    if _TABLE not in existing:
        return
    quoted = bind.dialect.identifier_preparer.quote(_TABLE)
    policy = bind.dialect.identifier_preparer.quote(_POLICY)
    op.execute(sa.text(f"ALTER TABLE {quoted} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {quoted} FORCE ROW LEVEL SECURITY"))
    op.execute(
        sa.text(
            f"CREATE POLICY {policy} ON {quoted} "
            f"USING ({_PREDICATE}) WITH CHECK ({_PREDICATE})"
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    existing = set(sa.inspect(bind).get_table_names())
    if _TABLE not in existing:
        return
    quoted = bind.dialect.identifier_preparer.quote(_TABLE)
    policy = bind.dialect.identifier_preparer.quote(_POLICY)
    op.execute(sa.text(f"DROP POLICY IF EXISTS {policy} ON {quoted}"))
    op.execute(sa.text(f"ALTER TABLE {quoted} NO FORCE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"ALTER TABLE {quoted} DISABLE ROW LEVEL SECURITY"))


__all__ = ["_POLICY", "_TABLE"]
