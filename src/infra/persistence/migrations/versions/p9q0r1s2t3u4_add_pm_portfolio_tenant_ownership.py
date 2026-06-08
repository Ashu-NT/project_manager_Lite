"""Add tenant ownership to PM portfolio records.

Revision ID: p9q0r1s2t3u4
Revises: o8p9q0r1s2t3
Create Date: 2026-06-08
"""

from __future__ import annotations

from collections.abc import Iterable

import sqlalchemy as sa
from alembic import op


revision = "p9q0r1s2t3u4"
down_revision = "o8p9q0r1s2t3"
branch_labels = None
depends_on = None


PORTFOLIO_TABLES = (
    "portfolio_scoring_templates",
    "portfolio_intake_items",
    "portfolio_scenarios",
)


def _table_exists(inspector: sa.Inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def _index_names(inspector: sa.Inspector, table_name: str) -> set[str]:
    if not _table_exists(inspector, table_name):
        return set()
    return {index["name"] for index in inspector.get_indexes(table_name)}


def _first_scalar(connection: sa.Connection, sql: str) -> str | None:
    row = connection.execute(sa.text(sql)).first()
    if row is None:
        return None
    value = row[0]
    return str(value) if value else None


def _default_organization_id(connection: sa.Connection, inspector: sa.Inspector) -> str | None:
    if not _table_exists(inspector, "organizations"):
        return None

    columns = _column_names(inspector, "organizations")
    order_column = "created_at" if "created_at" in columns else "id"

    if "is_active" in columns:
        active = _first_scalar(
            connection,
            f"SELECT id FROM organizations WHERE is_active = 1 ORDER BY {order_column} LIMIT 1",
        )
        if active:
            return active

    return _first_scalar(
        connection,
        f"SELECT id FROM organizations ORDER BY {order_column} LIMIT 1",
    )


def _add_organization_columns(inspector: sa.Inspector) -> None:
    for table_name in PORTFOLIO_TABLES:
        if not _table_exists(inspector, table_name):
            continue
        if "organization_id" in _column_names(inspector, table_name):
            continue
        op.add_column(
            table_name,
            sa.Column("organization_id", sa.String(length=64), nullable=True),
        )


def _backfill_organization_id(
    connection: sa.Connection,
    inspector: sa.Inspector,
    *,
    organization_id: str | None,
) -> None:
    if not organization_id:
        return

    for table_name in PORTFOLIO_TABLES:
        if "organization_id" not in _column_names(inspector, table_name):
            continue
        connection.execute(
            sa.text(
                f"""
                UPDATE {table_name}
                   SET organization_id = :organization_id
                 WHERE organization_id IS NULL
                    OR organization_id = ''
                """
            ),
            {"organization_id": organization_id},
        )


def _create_index_if_missing(
    inspector: sa.Inspector,
    table_name: str,
    index_name: str,
    columns: Iterable[str],
) -> None:
    if not _table_exists(inspector, table_name):
        return
    if index_name in _index_names(inspector, table_name):
        return
    table_columns = _column_names(inspector, table_name)
    if any(column not in table_columns for column in columns):
        return
    op.create_index(index_name, table_name, list(columns))


def upgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    _add_organization_columns(inspector)
    inspector = sa.inspect(connection)

    _backfill_organization_id(
        connection,
        inspector,
        organization_id=_default_organization_id(connection, inspector),
    )
    inspector = sa.inspect(connection)

    _create_index_if_missing(
        inspector,
        "portfolio_scoring_templates",
        "idx_portfolio_scoring_org_active",
        ("organization_id", "is_active"),
    )
    _create_index_if_missing(
        inspector,
        "portfolio_intake_items",
        "idx_portfolio_intake_org_status",
        ("organization_id", "status"),
    )
    _create_index_if_missing(
        inspector,
        "portfolio_scenarios",
        "idx_portfolio_scenarios_org_updated",
        ("organization_id", "updated_at"),
    )


def _drop_index_if_exists(inspector: sa.Inspector, table_name: str, index_name: str) -> None:
    if not _table_exists(inspector, table_name):
        return
    if index_name not in _index_names(inspector, table_name):
        return
    op.drop_index(index_name, table_name=table_name)


def _drop_column_if_exists(inspector: sa.Inspector, table_name: str, column_name: str) -> None:
    if not _table_exists(inspector, table_name):
        return
    if column_name not in _column_names(inspector, table_name):
        return
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.drop_column(column_name)


def downgrade() -> None:
    connection = op.get_bind()
    inspector = sa.inspect(connection)

    _drop_index_if_exists(
        inspector,
        "portfolio_scenarios",
        "idx_portfolio_scenarios_org_updated",
    )
    _drop_index_if_exists(
        inspector,
        "portfolio_intake_items",
        "idx_portfolio_intake_org_status",
    )
    _drop_index_if_exists(
        inspector,
        "portfolio_scoring_templates",
        "idx_portfolio_scoring_org_active",
    )
    inspector = sa.inspect(connection)

    for table_name in reversed(PORTFOLIO_TABLES):
        _drop_column_if_exists(inspector, table_name, "organization_id")
        inspector = sa.inspect(connection)
