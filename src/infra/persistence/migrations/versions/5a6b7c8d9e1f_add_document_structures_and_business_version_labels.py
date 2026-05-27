"""add document structures and business version labels

Revision ID: 5a6b7c8d9e1f
Revises: 4e7f9a1c2d3b
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa


revision = "5a6b7c8d9e1f"
down_revision = "4e7f9a1c2d3b"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def upgrade() -> None:
    if _has_table("organizations") and not _has_table("document_structures"):
        op.create_table(
            "document_structures",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("organization_id", sa.String(), nullable=False),
            sa.Column("structure_code", sa.String(length=64), nullable=False),
            sa.Column("name", sa.String(length=256), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("parent_structure_id", sa.String(), nullable=True),
            sa.Column("object_scope", sa.String(length=128), nullable=False, server_default="GENERAL"),
            sa.Column("default_document_type", sa.String(length=64), nullable=False, server_default="GENERAL"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["parent_structure_id"], ["document_structures.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("organization_id", "structure_code", name="ux_document_structures_org_code"),
        )
    if _has_table("document_structures") and not _has_index("document_structures", "idx_document_structures_organization"):
        op.create_index("idx_document_structures_organization", "document_structures", ["organization_id"], unique=False)
    if _has_table("document_structures") and not _has_index("document_structures", "idx_document_structures_parent"):
        op.create_index("idx_document_structures_parent", "document_structures", ["parent_structure_id"], unique=False)

    if _has_table("documents"):
        needs_structure_id = not _has_column("documents", "document_structure_id")
        needs_business_version_label = not _has_column("documents", "business_version_label")
        if needs_structure_id or needs_business_version_label:
            with op.batch_alter_table("documents") as batch:
                if needs_structure_id:
                    batch.add_column(sa.Column("document_structure_id", sa.String(), nullable=True))
                    batch.create_foreign_key(
                        "fk_documents_document_structure_id",
                        "document_structures",
                        ["document_structure_id"],
                        ["id"],
                        ondelete="SET NULL",
                    )
                if needs_business_version_label:
                    batch.add_column(sa.Column("business_version_label", sa.String(length=64), nullable=True))

        bind = op.get_bind()
        if _has_column("documents", "business_version_label") and _has_column("documents", "revision"):
            bind.execute(
                sa.text(
                    "UPDATE documents "
                    "SET business_version_label = revision "
                    "WHERE (business_version_label IS NULL OR business_version_label = '') "
                    "AND revision IS NOT NULL "
                    "AND revision <> ''"
                )
            )

        if _has_column("documents", "document_structure_id") and not _has_index("documents", "idx_documents_structure"):
            op.create_index("idx_documents_structure", "documents", ["document_structure_id"], unique=False)


def downgrade() -> None:
    if _has_index("documents", "idx_documents_structure"):
        op.drop_index("idx_documents_structure", table_name="documents")

    if _has_table("documents"):
        has_business_version_label = _has_column("documents", "business_version_label")
        has_structure_id = _has_column("documents", "document_structure_id")
        if has_business_version_label or has_structure_id:
            with op.batch_alter_table("documents") as batch:
                if has_business_version_label:
                    batch.drop_column("business_version_label")
                if has_structure_id:
                    batch.drop_column("document_structure_id")

    if _has_index("document_structures", "idx_document_structures_parent"):
        op.drop_index("idx_document_structures_parent", table_name="document_structures")
    if _has_index("document_structures", "idx_document_structures_organization"):
        op.drop_index("idx_document_structures_organization", table_name="document_structures")
    if _has_table("document_structures"):
        op.drop_table("document_structures")
