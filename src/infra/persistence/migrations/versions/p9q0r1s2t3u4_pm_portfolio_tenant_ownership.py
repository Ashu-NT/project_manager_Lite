"""Add tenant ownership to PM portfolio records.

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
"""

from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from alembic import op


revision = "p9q0r1s2t3u4"
down_revision = "o8p9q0r1s2t3"
branch_labels = None
depends_on = None


_PORTFOLIO_TABLES = (
    "portfolio_scoring_templates",
    "portfolio_intake_items",
    "portfolio_scenarios",
)


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in set(inspector.get_table_names())


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    if not _table_exists(inspector, table_name):
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _ensure_default_organization(connection, inspector) -> str | None:
    if not _table_exists(inspector, "organizations"):
        return None
    row = connection.execute(
        sa.text(
            """
            SELECT id
            FROM organizations
            ORDER BY
                CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                display_name ASC
            LIMIT 1
            """
        )
    ).first()
    if row is not None:
        return str(row[0])

    organization_id = "default-org"
    columns = {column["name"] for column in inspector.get_columns("organizations")}
    now = datetime.utcnow()
    values: dict[str, object] = {}
    if "id" in columns:
        values["id"] = organization_id
    if "organization_code" in columns:
        values["organization_code"] = "DEFAULT"
    if "display_name" in columns:
        values["display_name"] = "Default Organization"
    if "slug" in columns:
        values["slug"] = "default"
    if "timezone_name" in columns:
        values["timezone_name"] = "UTC"
    if "base_currency" in columns:
        values["base_currency"] = "EUR"
    if "is_active" in columns:
        values["is_active"] = True
    if "status" in columns:
        values["status"] = "ACTIVE"
    if "created_at" in columns:
        values["created_at"] = now
    if "updated_at" in columns:
        values["updated_at"] = now
    if "version" in columns:
        values["version"] = 1

    if values:
        column_names = ", ".join(values)
        bind_names = ", ".join(f":{name}" for name in values)
        connection.execute(
            sa.text(f"INSERT INTO organizations ({column_names}) VALUES ({bind_names})"),
            values,
        )
    return organization_id


def _add_organization_column_if_missing(inspector, table_name: str) -> None:
    if not _table_exists(inspector, table_name):
        return
    if _column_exists(inspector, table_name, "organization_id"):
        return
    with op.batch_alter_table(table_name) as batch:
        batch.add_column(sa.Column("organization_id", sa.String(), nullable=True))


def _backfill_table(connection, table_name: str, organization_id: str | None) -> None:
    if not organization_id:
        return
    connection.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET organization_id = :organization_id
            WHERE organization_id IS NULL OR organization_id = ''
            """
        ),
        {"organization_id": organization_id},
    )


def _create_index_if_possible(inspector, table_name: str, index_name: str, columns: list[str]) -> None:
    if not _table_exists(inspector, table_name):
        return
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in existing:
        return
    op.create_index(index_name, table_name, columns)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    organization_id = _ensure_default_organization(bind, inspector)

    for table_name in _PORTFOLIO_TABLES:
        _add_organization_column_if_missing(inspector, table_name)

    inspector = sa.inspect(bind)
    for table_name in _PORTFOLIO_TABLES:
        if _column_exists(inspector, table_name, "organization_id"):
            _backfill_table(bind, table_name, organization_id)

    inspector = sa.inspect(bind)
    _create_index_if_possible(
        inspector,
        "portfolio_scoring_templates",
        "idx_portfolio_scoring_org_active",
        ["organization_id", "is_active"],
    )
    _create_index_if_possible(
        inspector,
        "portfolio_intake_items",
        "idx_portfolio_intake_org_status",
        ["organization_id", "status"],
    )
    _create_index_if_possible(
        inspector,
        "portfolio_scenarios",
        "idx_portfolio_scenarios_org_updated",
        ["organization_id", "updated_at"],
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    for table_name, index_name in (
        ("portfolio_scoring_templates", "idx_portfolio_scoring_org_active"),
        ("portfolio_intake_items", "idx_portfolio_intake_org_status"),
        ("portfolio_scenarios", "idx_portfolio_scenarios_org_updated"),
    ):
        if _table_exists(inspector, table_name):
            existing = {index["name"] for index in inspector.get_indexes(table_name)}
            if index_name in existing:
                op.drop_index(index_name, table_name=table_name)

    inspector = sa.inspect(op.get_bind())
    for table_name in reversed(_PORTFOLIO_TABLES):
        if _column_exists(inspector, table_name, "organization_id"):
            with op.batch_alter_table(table_name) as batch:
                batch.drop_column("organization_id")
