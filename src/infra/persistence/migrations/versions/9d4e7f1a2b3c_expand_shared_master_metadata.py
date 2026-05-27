"""expand shared site, department, and document metadata

Revision ID: 9d4e7f1a2b3c
Revises: 8c4d1e2f7a9b
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "9d4e7f1a2b3c"
down_revision = "8c4d1e2f7a9b"
branch_labels = None
depends_on = None

_DEPARTMENTS_SITE_FK = "fk_departments_site_id_sites"
_DEPARTMENTS_PARENT_FK = "fk_departments_parent_department_id_departments"
_DEPARTMENTS_MANAGER_FK = "fk_departments_manager_employee_id_employees"
_DOCUMENTS_UPLOADED_BY_FK = "fk_documents_uploaded_by_user_id_users"


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


def _has_fk(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(fk.get("name") == constraint_name for fk in _inspector().get_foreign_keys(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table("sites"):
        with op.batch_alter_table("sites") as batch:
            if _has_column("sites", "display_name") and not _has_column("sites", "name"):
                batch.alter_column("display_name", new_column_name="name")
            if not _has_column("sites", "description"):
                batch.add_column(sa.Column("description", sa.Text(), nullable=True))
            if not _has_column("sites", "country"):
                batch.add_column(sa.Column("country", sa.String(length=128), nullable=True))
            if not _has_column("sites", "region"):
                batch.add_column(sa.Column("region", sa.String(length=128), nullable=True))
            if not _has_column("sites", "city"):
                batch.add_column(sa.Column("city", sa.String(length=128), nullable=True))
            if not _has_column("sites", "address_line_1"):
                batch.add_column(sa.Column("address_line_1", sa.String(length=256), nullable=True))
            if not _has_column("sites", "address_line_2"):
                batch.add_column(sa.Column("address_line_2", sa.String(length=256), nullable=True))
            if not _has_column("sites", "postal_code"):
                batch.add_column(sa.Column("postal_code", sa.String(length=64), nullable=True))
            if not _has_column("sites", "timezone"):
                batch.add_column(sa.Column("timezone", sa.String(length=128), nullable=True))
            if not _has_column("sites", "currency_code"):
                batch.add_column(sa.Column("currency_code", sa.String(length=8), nullable=True))
            if not _has_column("sites", "site_type"):
                batch.add_column(sa.Column("site_type", sa.String(length=128), nullable=True))
            if not _has_column("sites", "status"):
                batch.add_column(sa.Column("status", sa.String(length=64), nullable=True))
            if not _has_column("sites", "default_calendar_id"):
                batch.add_column(sa.Column("default_calendar_id", sa.String(length=64), nullable=True))
            if not _has_column("sites", "default_language"):
                batch.add_column(sa.Column("default_language", sa.String(length=32), nullable=True))
            if not _has_column("sites", "opened_at"):
                batch.add_column(sa.Column("opened_at", sa.DateTime(), nullable=True))
            if not _has_column("sites", "closed_at"):
                batch.add_column(sa.Column("closed_at", sa.DateTime(), nullable=True))
            if not _has_column("sites", "created_at"):
                batch.add_column(
                    sa.Column(
                        "created_at",
                        sa.DateTime(),
                        nullable=False,
                        server_default=sa.text("CURRENT_TIMESTAMP"),
                    )
                )
            if not _has_column("sites", "updated_at"):
                batch.add_column(
                    sa.Column(
                        "updated_at",
                        sa.DateTime(),
                        nullable=False,
                        server_default=sa.text("CURRENT_TIMESTAMP"),
                    )
                )
            if not _has_column("sites", "notes"):
                batch.add_column(sa.Column("notes", sa.Text(), nullable=True))
        bind.execute(
            sa.text(
                "UPDATE sites SET status = CASE WHEN is_active = 1 THEN 'ACTIVE' ELSE 'INACTIVE' END "
                "WHERE status IS NULL OR status = ''"
            )
        )
        bind.execute(sa.text("UPDATE sites SET default_calendar_id = 'default' WHERE default_calendar_id IS NULL"))

    if _has_table("departments"):
        with op.batch_alter_table("departments") as batch:
            if _has_column("departments", "display_name") and not _has_column("departments", "name"):
                batch.alter_column("display_name", new_column_name="name")
            if not _has_column("departments", "description"):
                batch.add_column(sa.Column("description", sa.Text(), nullable=True))
            if not _has_column("departments", "site_id"):
                batch.add_column(sa.Column("site_id", sa.String(), nullable=True))
            if not _has_column("departments", "parent_department_id"):
                batch.add_column(sa.Column("parent_department_id", sa.String(), nullable=True))
            if not _has_column("departments", "department_type"):
                batch.add_column(sa.Column("department_type", sa.String(length=128), nullable=True))
            if not _has_column("departments", "cost_center_code"):
                batch.add_column(sa.Column("cost_center_code", sa.String(length=64), nullable=True))
            if not _has_column("departments", "manager_employee_id"):
                batch.add_column(sa.Column("manager_employee_id", sa.String(), nullable=True))
            if not _has_column("departments", "created_at"):
                batch.add_column(
                    sa.Column(
                        "created_at",
                        sa.DateTime(),
                        nullable=False,
                        server_default=sa.text("CURRENT_TIMESTAMP"),
                    )
                )
            if not _has_column("departments", "updated_at"):
                batch.add_column(
                    sa.Column(
                        "updated_at",
                        sa.DateTime(),
                        nullable=False,
                        server_default=sa.text("CURRENT_TIMESTAMP"),
                    )
                )
            if not _has_column("departments", "notes"):
                batch.add_column(sa.Column("notes", sa.Text(), nullable=True))
        if not _has_fk("departments", _DEPARTMENTS_SITE_FK):
            with op.batch_alter_table("departments") as batch:
                batch.create_foreign_key(
                    _DEPARTMENTS_SITE_FK,
                    "sites",
                    ["site_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_fk("departments", _DEPARTMENTS_PARENT_FK):
            with op.batch_alter_table("departments") as batch:
                batch.create_foreign_key(
                    _DEPARTMENTS_PARENT_FK,
                    "departments",
                    ["parent_department_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_fk("departments", _DEPARTMENTS_MANAGER_FK):
            with op.batch_alter_table("departments") as batch:
                batch.create_foreign_key(
                    _DEPARTMENTS_MANAGER_FK,
                    "employees",
                    ["manager_employee_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_index("departments", "idx_departments_site"):
            op.create_index("idx_departments_site", "departments", ["site_id"], unique=False)
        if not _has_index("departments", "idx_departments_manager"):
            op.create_index("idx_departments_manager", "departments", ["manager_employee_id"], unique=False)

    if _has_table("documents"):
        with op.batch_alter_table("documents") as batch:
            if _has_column("documents", "classification") and not _has_column("documents", "document_type"):
                batch.alter_column("classification", new_column_name="document_type")
            if _has_column("documents", "storage_ref") and not _has_column("documents", "storage_uri"):
                batch.alter_column("storage_ref", new_column_name="storage_uri")
            if not _has_column("documents", "file_name"):
                batch.add_column(sa.Column("file_name", sa.String(length=256), nullable=True))
            if not _has_column("documents", "mime_type"):
                batch.add_column(sa.Column("mime_type", sa.String(length=128), nullable=True))
            if not _has_column("documents", "source_system"):
                batch.add_column(sa.Column("source_system", sa.String(length=128), nullable=True))
            if not _has_column("documents", "uploaded_at"):
                batch.add_column(
                    sa.Column(
                        "uploaded_at",
                        sa.DateTime(),
                        nullable=False,
                        server_default=sa.text("CURRENT_TIMESTAMP"),
                    )
                )
            if not _has_column("documents", "uploaded_by_user_id"):
                batch.add_column(sa.Column("uploaded_by_user_id", sa.String(), nullable=True))
            if not _has_column("documents", "effective_date"):
                batch.add_column(sa.Column("effective_date", sa.Date(), nullable=True))
            if not _has_column("documents", "review_date"):
                batch.add_column(sa.Column("review_date", sa.Date(), nullable=True))
            if not _has_column("documents", "confidentiality_level"):
                batch.add_column(sa.Column("confidentiality_level", sa.String(length=64), nullable=True))
            if not _has_column("documents", "revision"):
                batch.add_column(sa.Column("revision", sa.String(length=64), nullable=True))
            if not _has_column("documents", "is_current"):
                batch.add_column(
                    sa.Column(
                        "is_current",
                        sa.Boolean(),
                        nullable=False,
                        server_default="1",
                    )
                )
        bind.execute(
            sa.text(
                "UPDATE documents SET source_system = 'platform' "
                "WHERE source_system IS NULL OR source_system = ''"
            )
        )
        bind.execute(
            sa.text(
                "UPDATE documents SET is_current = 1 "
                "WHERE is_current IS NULL"
            )
        )
        if not _has_fk("documents", _DOCUMENTS_UPLOADED_BY_FK):
            with op.batch_alter_table("documents") as batch:
                batch.create_foreign_key(
                    _DOCUMENTS_UPLOADED_BY_FK,
                    "users",
                    ["uploaded_by_user_id"],
                    ["id"],
                    ondelete="SET NULL",
                )
        if not _has_index("documents", "idx_documents_uploaded_by"):
            op.create_index("idx_documents_uploaded_by", "documents", ["uploaded_by_user_id"], unique=False)


def downgrade() -> None:
    if _has_index("documents", "idx_documents_uploaded_by"):
        op.drop_index("idx_documents_uploaded_by", table_name="documents")
    if _has_table("documents"):
        with op.batch_alter_table("documents") as batch:
            if _has_fk("documents", _DOCUMENTS_UPLOADED_BY_FK):
                batch.drop_constraint(_DOCUMENTS_UPLOADED_BY_FK, type_="foreignkey")
            if _has_column("documents", "is_current"):
                batch.drop_column("is_current")
            if _has_column("documents", "revision"):
                batch.drop_column("revision")
            if _has_column("documents", "confidentiality_level"):
                batch.drop_column("confidentiality_level")
            if _has_column("documents", "review_date"):
                batch.drop_column("review_date")
            if _has_column("documents", "effective_date"):
                batch.drop_column("effective_date")
            if _has_column("documents", "uploaded_by_user_id"):
                batch.drop_column("uploaded_by_user_id")
            if _has_column("documents", "uploaded_at"):
                batch.drop_column("uploaded_at")
            if _has_column("documents", "source_system"):
                batch.drop_column("source_system")
            if _has_column("documents", "mime_type"):
                batch.drop_column("mime_type")
            if _has_column("documents", "file_name"):
                batch.drop_column("file_name")
            if _has_column("documents", "storage_uri") and not _has_column("documents", "storage_ref"):
                batch.alter_column("storage_uri", new_column_name="storage_ref")
            if _has_column("documents", "document_type") and not _has_column("documents", "classification"):
                batch.alter_column("document_type", new_column_name="classification")

    if _has_index("departments", "idx_departments_manager"):
        op.drop_index("idx_departments_manager", table_name="departments")
    if _has_index("departments", "idx_departments_site"):
        op.drop_index("idx_departments_site", table_name="departments")
    if _has_table("departments"):
        with op.batch_alter_table("departments") as batch:
            if _has_fk("departments", _DEPARTMENTS_MANAGER_FK):
                batch.drop_constraint(_DEPARTMENTS_MANAGER_FK, type_="foreignkey")
            if _has_fk("departments", _DEPARTMENTS_PARENT_FK):
                batch.drop_constraint(_DEPARTMENTS_PARENT_FK, type_="foreignkey")
            if _has_fk("departments", _DEPARTMENTS_SITE_FK):
                batch.drop_constraint(_DEPARTMENTS_SITE_FK, type_="foreignkey")
            if _has_column("departments", "notes"):
                batch.drop_column("notes")
            if _has_column("departments", "updated_at"):
                batch.drop_column("updated_at")
            if _has_column("departments", "created_at"):
                batch.drop_column("created_at")
            if _has_column("departments", "manager_employee_id"):
                batch.drop_column("manager_employee_id")
            if _has_column("departments", "cost_center_code"):
                batch.drop_column("cost_center_code")
            if _has_column("departments", "department_type"):
                batch.drop_column("department_type")
            if _has_column("departments", "parent_department_id"):
                batch.drop_column("parent_department_id")
            if _has_column("departments", "site_id"):
                batch.drop_column("site_id")
            if _has_column("departments", "description"):
                batch.drop_column("description")
            if _has_column("departments", "name") and not _has_column("departments", "display_name"):
                batch.alter_column("name", new_column_name="display_name")

    if _has_table("sites"):
        with op.batch_alter_table("sites") as batch:
            if _has_column("sites", "notes"):
                batch.drop_column("notes")
            if _has_column("sites", "updated_at"):
                batch.drop_column("updated_at")
            if _has_column("sites", "created_at"):
                batch.drop_column("created_at")
            if _has_column("sites", "closed_at"):
                batch.drop_column("closed_at")
            if _has_column("sites", "opened_at"):
                batch.drop_column("opened_at")
            if _has_column("sites", "default_language"):
                batch.drop_column("default_language")
            if _has_column("sites", "default_calendar_id"):
                batch.drop_column("default_calendar_id")
            if _has_column("sites", "status"):
                batch.drop_column("status")
            if _has_column("sites", "site_type"):
                batch.drop_column("site_type")
            if _has_column("sites", "currency_code"):
                batch.drop_column("currency_code")
            if _has_column("sites", "timezone"):
                batch.drop_column("timezone")
            if _has_column("sites", "postal_code"):
                batch.drop_column("postal_code")
            if _has_column("sites", "address_line_2"):
                batch.drop_column("address_line_2")
            if _has_column("sites", "address_line_1"):
                batch.drop_column("address_line_1")
            if _has_column("sites", "city"):
                batch.drop_column("city")
            if _has_column("sites", "region"):
                batch.drop_column("region")
            if _has_column("sites", "country"):
                batch.drop_column("country")
            if _has_column("sites", "description"):
                batch.drop_column("description")
            if _has_column("sites", "name") and not _has_column("sites", "display_name"):
                batch.alter_column("name", new_column_name="display_name")
