"""Canonical Audit evidence model: category/result/before-after replace compliance_tag/field/old_value/new_value.

Revision ID: d4f8b3e6a917
Revises: a2f5c8d3b917
Create Date: 2026-09-16

`audit_entries` gains the full evidence/actor/trace column set (category,
result, failure_code, before/after/changed_fields snapshots, actor_display_name,
session_id, authentication_method, impersonated_by_actor_id, service_account_id,
entity_version, project_id, correlation_id, causation_id, permission_used,
approval_request_id, reason). Existing `compliance_tag` values are backfilled
into `category` (financial -> FINANCIAL, SOC2 -> SECURITY, else COMPLIANCE)
and existing `field`/`old_value`/`new_value` triples are folded into a single
`changed_fields_json` entry before the old columns are dropped -- no dual
schema is kept afterward.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4f8b3e6a917"
down_revision: str | Sequence[str] | None = "a2f5c8d3b917"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "audit_entries"

_NEW_COLUMNS = (
    ("actor_display_name", sa.String(length=256)),
    ("session_id", sa.String()),
    ("authentication_method", sa.String(length=32)),
    ("impersonated_by_actor_id", sa.String()),
    ("service_account_id", sa.String()),
    ("entity_version", sa.String(length=32)),
    ("failure_code", sa.String(length=64)),
    ("before_data_json", sa.Text()),
    ("after_data_json", sa.Text()),
    ("changed_fields_json", sa.Text()),
    ("project_id", sa.String()),
    ("correlation_id", sa.String()),
    ("causation_id", sa.String()),
    ("permission_used", sa.String(length=128)),
    ("approval_request_id", sa.String()),
    ("reason", sa.Text()),
)


def upgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        for name, col_type in _NEW_COLUMNS:
            batch_op.add_column(sa.Column(name, col_type, nullable=True))
        batch_op.add_column(
            sa.Column(
                "category",
                sa.String(length=32),
                nullable=False,
                server_default="COMPLIANCE",
            )
        )
        batch_op.add_column(
            sa.Column(
                "result",
                sa.String(length=16),
                nullable=False,
                server_default="SUCCESS",
            )
        )

    audit_entries = sa.table(
        _TABLE,
        sa.column("id", sa.String()),
        sa.column("compliance_tag", sa.String()),
        sa.column("category", sa.String()),
        sa.column("field", sa.String()),
        sa.column("old_value", sa.Text()),
        sa.column("new_value", sa.Text()),
        sa.column("changed_fields_json", sa.Text()),
    )
    connection = op.get_bind()

    connection.execute(
        audit_entries.update()
        .where(audit_entries.c.compliance_tag == "financial")
        .values(category="FINANCIAL")
    )
    connection.execute(
        audit_entries.update()
        .where(audit_entries.c.compliance_tag == "SOC2")
        .values(category="SECURITY")
    )

    rows = connection.execute(
        sa.select(
            audit_entries.c.id,
            audit_entries.c.field,
            audit_entries.c.old_value,
            audit_entries.c.new_value,
        ).where(audit_entries.c.field.isnot(None))
    ).fetchall()
    for row in rows:
        import json

        changed = {row.field: {"before": row.old_value, "after": row.new_value}}
        connection.execute(
            audit_entries.update()
            .where(audit_entries.c.id == row.id)
            .values(changed_fields_json=json.dumps(changed, sort_keys=True))
        )

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.drop_index("idx_audit_entries_compliance")
        batch_op.drop_column("compliance_tag")
        batch_op.drop_column("field")
        batch_op.drop_column("old_value")
        batch_op.drop_column("new_value")
        batch_op.alter_column("module", server_default="platform")
        batch_op.alter_column("source", server_default="DESKTOP_UI")
        batch_op.create_index("idx_audit_entries_category", ["category", "timestamp"], unique=False)
        batch_op.create_index("idx_audit_entries_project", ["project_id", "timestamp"], unique=False)
        batch_op.create_index("idx_audit_entries_correlation", ["correlation_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.drop_index("idx_audit_entries_correlation")
        batch_op.drop_index("idx_audit_entries_project")
        batch_op.drop_index("idx_audit_entries_category")
        batch_op.add_column(sa.Column("field", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("old_value", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("new_value", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("compliance_tag", sa.String(length=32), nullable=False, server_default="none")
        )
        batch_op.alter_column("source", server_default="api")

    audit_entries = sa.table(
        _TABLE,
        sa.column("id", sa.String()),
        sa.column("category", sa.String()),
        sa.column("compliance_tag", sa.String()),
    )
    connection = op.get_bind()
    connection.execute(
        audit_entries.update()
        .where(audit_entries.c.category == "FINANCIAL")
        .values(compliance_tag="financial")
    )
    connection.execute(
        audit_entries.update()
        .where(audit_entries.c.category == "SECURITY")
        .values(compliance_tag="SOC2")
    )

    with op.batch_alter_table(_TABLE, schema=None) as batch_op:
        batch_op.create_index("idx_audit_entries_compliance", ["compliance_tag", "timestamp"], unique=False)
        batch_op.drop_column("result")
        batch_op.drop_column("category")
        for name, _ in reversed(_NEW_COLUMNS):
            batch_op.drop_column(name)
