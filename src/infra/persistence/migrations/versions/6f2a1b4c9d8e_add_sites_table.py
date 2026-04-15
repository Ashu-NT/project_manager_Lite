"""add shared sites table

Revision ID: 6f2a1b4c9d8e
Revises: 5c1b7d9e2a4f
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "6f2a1b4c9d8e"
down_revision = "5c1b7d9e2a4f"
branch_labels = None
depends_on = None

_SITES_ORG_FK = "fk_sites_organization_id_organizations"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _has_fk(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(fk.get("name") == constraint_name for fk in _inspector().get_foreign_keys(table_name))


def upgrade() -> None:
    if not _has_table("sites"):
        op.create_table(
            "sites",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("site_code", sa.String(length=64), nullable=False),
            sa.Column("display_name", sa.String(length=256), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name=_SITES_ORG_FK,
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "site_code", name="ux_sites_org_code"),
        )

    if not _has_index("sites", "idx_sites_organization"):
        op.create_index("idx_sites_organization", "sites", ["organization_id"], unique=False)
    if not _has_index("sites", "idx_sites_active"):
        op.create_index("idx_sites_active", "sites", ["organization_id", "is_active"], unique=False)


def downgrade() -> None:
    if _has_index("sites", "idx_sites_active"):
        op.drop_index("idx_sites_active", table_name="sites")
    if _has_index("sites", "idx_sites_organization"):
        op.drop_index("idx_sites_organization", table_name="sites")
    if _has_table("sites"):
        if _has_fk("sites", _SITES_ORG_FK):
            with op.batch_alter_table("sites") as batch:
                batch.drop_constraint(_SITES_ORG_FK, type_="foreignkey")
        op.drop_table("sites")
