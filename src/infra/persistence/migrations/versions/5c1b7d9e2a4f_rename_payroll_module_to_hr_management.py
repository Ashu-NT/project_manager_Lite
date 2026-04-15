"""rename payroll module entitlements to hr management

Revision ID: 5c1b7d9e2a4f
Revises: f1e2d3c4b5a6
Create Date: 2026-03-19
"""

from alembic import op
import sqlalchemy as sa


revision = "5c1b7d9e2a4f"
down_revision = "f1e2d3c4b5a6"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def upgrade() -> None:
    table_name = "organization_module_entitlements"
    if not _has_table(table_name):
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"""
            DELETE FROM {table_name}
            WHERE module_code = 'payroll'
              AND EXISTS (
                SELECT 1
                FROM {table_name} AS canonical
                WHERE canonical.organization_id = {table_name}.organization_id
                  AND canonical.module_code = 'hr_management'
              )
            """
        )
    )
    bind.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET module_code = 'hr_management'
            WHERE module_code = 'payroll'
            """
        )
    )


def downgrade() -> None:
    table_name = "organization_module_entitlements"
    if not _has_table(table_name):
        return
    bind = op.get_bind()
    bind.execute(
        sa.text(
            f"""
            DELETE FROM {table_name}
            WHERE module_code = 'hr_management'
              AND EXISTS (
                SELECT 1
                FROM {table_name} AS legacy
                WHERE legacy.organization_id = {table_name}.organization_id
                  AND legacy.module_code = 'payroll'
              )
            """
        )
    )
    bind.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET module_code = 'payroll'
            WHERE module_code = 'hr_management'
            """
        )
    )
