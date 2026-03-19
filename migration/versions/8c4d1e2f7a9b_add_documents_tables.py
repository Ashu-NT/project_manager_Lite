"""add shared documents tables

Revision ID: 8c4d1e2f7a9b
Revises: 7a1c5d8e4b2f
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "8c4d1e2f7a9b"
down_revision = "7a1c5d8e4b2f"
branch_labels = None
depends_on = None

_DOCUMENTS_ORG_FK = "fk_documents_organization_id_organizations"
_DOCUMENT_LINKS_ORG_FK = "fk_document_links_organization_id_organizations"
_DOCUMENT_LINKS_DOCUMENT_FK = "fk_document_links_document_id_documents"


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
    if not _has_table("documents"):
        op.create_table(
            "documents",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("document_code", sa.String(length=64), nullable=False),
            sa.Column("title", sa.String(length=256), nullable=False),
            sa.Column("classification", sa.String(length=64), nullable=False),
            sa.Column("storage_kind", sa.String(length=64), nullable=False),
            sa.Column("storage_ref", sa.Text(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name=_DOCUMENTS_ORG_FK,
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "document_code", name="ux_documents_org_code"),
        )

    if not _has_table("document_links"):
        op.create_table(
            "document_links",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("document_id", sa.String(), nullable=False),
            sa.Column("module_code", sa.String(length=128), nullable=False),
            sa.Column("entity_type", sa.String(length=128), nullable=False),
            sa.Column("entity_id", sa.String(length=128), nullable=False),
            sa.Column("link_role", sa.String(length=128), nullable=True),
            sa.ForeignKeyConstraint(
                ["organization_id"],
                ["organizations.id"],
                name=_DOCUMENT_LINKS_ORG_FK,
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["document_id"],
                ["documents.id"],
                name=_DOCUMENT_LINKS_DOCUMENT_FK,
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "document_id",
                "module_code",
                "entity_type",
                "entity_id",
                "link_role",
                name="ux_document_links_unique",
            ),
        )

    if not _has_index("documents", "idx_documents_organization"):
        op.create_index("idx_documents_organization", "documents", ["organization_id"], unique=False)
    if not _has_index("document_links", "idx_document_links_document"):
        op.create_index("idx_document_links_document", "document_links", ["document_id"], unique=False)
    if not _has_index("document_links", "idx_document_links_entity"):
        op.create_index(
            "idx_document_links_entity",
            "document_links",
            ["organization_id", "module_code", "entity_type", "entity_id"],
            unique=False,
        )


def downgrade() -> None:
    if _has_index("document_links", "idx_document_links_entity"):
        op.drop_index("idx_document_links_entity", table_name="document_links")
    if _has_index("document_links", "idx_document_links_document"):
        op.drop_index("idx_document_links_document", table_name="document_links")
    if _has_index("documents", "idx_documents_organization"):
        op.drop_index("idx_documents_organization", table_name="documents")
    if _has_table("document_links"):
        if _has_fk("document_links", _DOCUMENT_LINKS_DOCUMENT_FK) or _has_fk("document_links", _DOCUMENT_LINKS_ORG_FK):
            with op.batch_alter_table("document_links") as batch:
                if _has_fk("document_links", _DOCUMENT_LINKS_DOCUMENT_FK):
                    batch.drop_constraint(_DOCUMENT_LINKS_DOCUMENT_FK, type_="foreignkey")
                if _has_fk("document_links", _DOCUMENT_LINKS_ORG_FK):
                    batch.drop_constraint(_DOCUMENT_LINKS_ORG_FK, type_="foreignkey")
        op.drop_table("document_links")
    if _has_table("documents"):
        if _has_fk("documents", _DOCUMENTS_ORG_FK):
            with op.batch_alter_table("documents") as batch:
                batch.drop_constraint(_DOCUMENTS_ORG_FK, type_="foreignkey")
        op.drop_table("documents")
