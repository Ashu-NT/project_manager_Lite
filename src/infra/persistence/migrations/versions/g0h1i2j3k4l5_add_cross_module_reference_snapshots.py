"""add cross-module reference snapshot fields to reservations and requisitions

Adds source_module, source_entity_type, source_code_snapshot,
source_title_snapshot, and source_status_snapshot to the inventory reservation
and purchase requisition tables.  These soft-reference snapshot columns let the
UI display a readable label for the originating PM task or maintenance work order
even when the linked module is disabled or the source record has been deleted.

Revision ID: g0h1i2j3k4l5
Revises: c6d7e8f9a0b1
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa


revision = "g0h1i2j3k4l5"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    return any(c["name"] == column for c in _inspector().get_columns(table))


def upgrade() -> None:
    # --- inventory_stock_reservations ---
    _RESERVATION_COLS = [
        ("source_module", sa.String(64)),
        ("source_entity_type", sa.String(64)),
        ("source_code_snapshot", sa.String(128)),
        ("source_title_snapshot", sa.String(512)),
        ("source_status_snapshot", sa.String(64)),
    ]
    with op.batch_alter_table("inventory_stock_reservations") as batch:
        for col_name, col_type in _RESERVATION_COLS:
            if not _has_column("inventory_stock_reservations", col_name):
                batch.add_column(sa.Column(col_name, col_type, nullable=True))

    op.create_index(
        "idx_inventory_stock_reservations_source_module",
        "inventory_stock_reservations",
        ["source_module"],
        unique=False,
        if_not_exists=True,
    )

    # --- inventory_purchase_requisitions ---
    _REQUISITION_COLS = [
        ("source_module", sa.String(64)),
        ("source_entity_type", sa.String(64)),
        ("source_code_snapshot", sa.String(128)),
        ("source_title_snapshot", sa.String(512)),
        ("source_status_snapshot", sa.String(64)),
    ]
    with op.batch_alter_table("inventory_purchase_requisitions") as batch:
        for col_name, col_type in _REQUISITION_COLS:
            if not _has_column("inventory_purchase_requisitions", col_name):
                batch.add_column(sa.Column(col_name, col_type, nullable=True))

    op.create_index(
        "idx_inventory_purchase_requisitions_source_module",
        "inventory_purchase_requisitions",
        ["source_module"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    _COLS = [
        "source_module",
        "source_entity_type",
        "source_code_snapshot",
        "source_title_snapshot",
        "source_status_snapshot",
    ]

    with op.batch_alter_table("inventory_purchase_requisitions") as batch:
        try:
            batch.drop_index("idx_inventory_purchase_requisitions_source_module")
        except Exception:
            pass
        for col_name in _COLS:
            if _has_column("inventory_purchase_requisitions", col_name):
                batch.drop_column(col_name)

    with op.batch_alter_table("inventory_stock_reservations") as batch:
        try:
            batch.drop_index("idx_inventory_stock_reservations_source_module")
        except Exception:
            pass
        for col_name in _COLS:
            if _has_column("inventory_stock_reservations", col_name):
                batch.drop_column(col_name)
