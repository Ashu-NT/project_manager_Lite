"""Project Management: human-readable project_code

Adds projects.project_code (nullable), backfills every existing row with a
deterministic, unique, name-token code (PRJ-<NAME>-NNNN), then adds a unique
index. Reversible. See docs/PM_CODE_FIELDS_MIGRATION_PLAN.md (Phase A, Project).

Revision ID: l5m6n7o8p9q0
Revises: k4l5m6n7o8p9
Create Date: 2026-06-01
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "l5m6n7o8p9q0"
down_revision = "k4l5m6n7o8p9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    from src.core.platform.common.code_generation import generate_unique_code, sanitize_token

    op.add_column("projects", sa.Column("project_code", sa.String(64), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, name FROM projects ORDER BY id")).fetchall()
    assigned: set[str] = set()
    for row in rows:
        project_id = row[0]
        token = sanitize_token(row[1] or "")
        code = generate_unique_code(
            "PRJ", exists=lambda candidate: candidate in assigned, segment=token
        )
        assigned.add(code)
        bind.execute(
            sa.text("UPDATE projects SET project_code = :code WHERE id = :id"),
            {"code": code, "id": project_id},
        )

    op.create_index("ux_projects_code", "projects", ["project_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_projects_code", table_name="projects")
    op.drop_column("projects", "project_code")
