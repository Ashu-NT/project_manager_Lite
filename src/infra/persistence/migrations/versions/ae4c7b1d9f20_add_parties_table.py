"""add shared parties table

Revision ID: ae4c7b1d9f20
Revises: 9d4e7f1a2b3c
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "ae4c7b1d9f20"
down_revision = "9d4e7f1a2b3c"
branch_labels = None
depends_on = None

_PARTIES_ORG_FK = "fk_parties_organization_id_organizations"


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
    if not _has_table("parties"):
        op.create_table(
            "parties",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("party_code", sa.String(length=64), nullable=False),
            sa.Column("party_name", sa.String(length=256), nullable=False),
            sa.Column("party_type", sa.String(length=64), nullable=False),
            sa.Column("legal_name", sa.String(length=256), nullable=True),
            sa.Column("contact_name", sa.String(length=256), nullable=True),
            sa.Column("email", sa.String(length=256), nullable=True),
            sa.Column("phone", sa.String(length=64), nullable=True),
            sa.Column("country", sa.String(length=128), nullable=True),
            sa.Column("city", sa.String(length=128), nullable=True),
            sa.Column("address_line_1", sa.String(length=256), nullable=True),
            sa.Column("address_line_2", sa.String(length=256), nullable=True),
            sa.Column("postal_code", sa.String(length=64), nullable=True),
            sa.Column("website", sa.String(length=256), nullable=True),
            sa.Column("tax_registration_number", sa.String(length=128), nullable=True),
            sa.Column("external_reference", sa.String(length=128), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name=_PARTIES_ORG_FK,
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "party_code", name="ux_parties_org_code"),
        )

    if not _has_index("parties", "idx_parties_organization"):
        op.create_index("idx_parties_organization", "parties", ["organization_id"], unique=False)
    if not _has_index("parties", "idx_parties_active"):
        op.create_index("idx_parties_active", "parties", ["organization_id", "is_active"], unique=False)
    if not _has_index("parties", "idx_parties_type"):
        op.create_index("idx_parties_type", "parties", ["organization_id", "party_type"], unique=False)


def downgrade() -> None:
    if _has_index("parties", "idx_parties_type"):
        op.drop_index("idx_parties_type", table_name="parties")
    if _has_index("parties", "idx_parties_active"):
        op.drop_index("idx_parties_active", table_name="parties")
    if _has_index("parties", "idx_parties_organization"):
        op.drop_index("idx_parties_organization", table_name="parties")
    if _has_table("parties"):
        if _has_fk("parties", _PARTIES_ORG_FK):
            with op.batch_alter_table("parties") as batch:
                batch.drop_constraint(_PARTIES_ORG_FK, type_="foreignkey")
        op.drop_table("parties")
