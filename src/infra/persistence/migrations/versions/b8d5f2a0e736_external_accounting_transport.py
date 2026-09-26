"""Pin external delivery destinations and retain exact transport receipts."""

import sqlalchemy as sa
from alembic import op

revision = "b8d5f2a0e736"
down_revision = "a7c4e1b9d625"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project_accounting_outbox",
        sa.Column("target_adapter_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "project_accounting_outbox",
        sa.Column("target_connection_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "project_accounting_outbox",
        sa.Column("target_configuration_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "project_accounting_outbox",
        sa.Column("transport_receipt_json", sa.Text(), nullable=True),
    )
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("""
            CREATE FUNCTION guard_accounting_transport_identity() RETURNS trigger AS $$
            BEGIN
                IF (OLD.target_adapter_id IS NOT NULL AND
                    (NEW.target_adapter_id IS DISTINCT FROM OLD.target_adapter_id OR
                     NEW.target_connection_id IS DISTINCT FROM OLD.target_connection_id)) OR
                   (OLD.transport_receipt_json IS NOT NULL AND
                    NEW.transport_receipt_json IS DISTINCT FROM OLD.transport_receipt_json) THEN
                    RAISE EXCEPTION 'Accounting transport identity is immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            CREATE TRIGGER trg_accounting_transport_identity BEFORE UPDATE ON project_accounting_outbox
            FOR EACH ROW EXECUTE FUNCTION guard_accounting_transport_identity();
        """)
    elif dialect == "sqlite":
        op.execute("""
            CREATE TRIGGER trg_accounting_transport_identity BEFORE UPDATE ON project_accounting_outbox
            WHEN (OLD.target_adapter_id IS NOT NULL AND
                  (NEW.target_adapter_id IS NOT OLD.target_adapter_id OR
                   NEW.target_connection_id IS NOT OLD.target_connection_id)) OR
                 (OLD.transport_receipt_json IS NOT NULL AND
                  NEW.transport_receipt_json IS NOT OLD.transport_receipt_json)
            BEGIN SELECT RAISE(ABORT, 'Accounting transport identity is immutable'); END
        """)


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_accounting_transport_identity ON project_accounting_outbox"
        )
        op.execute("DROP FUNCTION IF EXISTS guard_accounting_transport_identity()")
    elif op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_accounting_transport_identity")
    for name in (
        "transport_receipt_json",
        "target_configuration_version",
        "target_connection_id",
        "target_adapter_id",
    ):
        op.drop_column("project_accounting_outbox", name)
