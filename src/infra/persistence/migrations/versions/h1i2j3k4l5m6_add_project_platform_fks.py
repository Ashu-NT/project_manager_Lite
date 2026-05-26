"""Add Platform FK columns to projects table.

Revision ID: h1i2j3k4l5m6
Revises: g0h1i2j3k4l5
Create Date: 2026-05-26

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "h1i2j3k4l5m6"
down_revision = "g0h1i2j3k4l5"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return column in {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    with op.batch_alter_table("projects", schema=None) as batch_op:
        if not _has_column("projects", "organization_id"):
            batch_op.add_column(
                sa.Column(
                    "organization_id",
                    sa.String(),
                    sa.ForeignKey("organizations.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )
        if not _has_column("projects", "site_id"):
            batch_op.add_column(
                sa.Column(
                    "site_id",
                    sa.String(),
                    sa.ForeignKey("sites.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )
        if not _has_column("projects", "client_party_id"):
            batch_op.add_column(
                sa.Column(
                    "client_party_id",
                    sa.String(),
                    sa.ForeignKey("parties.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )
        if not _has_column("projects", "manager_user_id"):
            batch_op.add_column(
                sa.Column(
                    "manager_user_id",
                    sa.String(),
                    sa.ForeignKey("users.id", ondelete="SET NULL"),
                    nullable=True,
                )
            )

    op.create_index(
        "idx_projects_organization_id",
        "projects",
        ["organization_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "idx_projects_site_id",
        "projects",
        ["site_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("idx_projects_site_id", table_name="projects")
    op.drop_index("idx_projects_organization_id", table_name="projects")
    with op.batch_alter_table("projects", schema=None) as batch_op:
        if _has_column("projects", "manager_user_id"):
            batch_op.drop_column("manager_user_id")
        if _has_column("projects", "client_party_id"):
            batch_op.drop_column("client_party_id")
        if _has_column("projects", "site_id"):
            batch_op.drop_column("site_id")
        if _has_column("projects", "organization_id"):
            batch_op.drop_column("organization_id")
