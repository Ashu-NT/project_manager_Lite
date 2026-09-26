"""Preserve authenticated Accounting inbox and business outcome evidence."""

from alembic import op

revision = "c9e6a3b1f847"
down_revision = "b8d5f2a0e736"
branch_labels = None
depends_on = None


def upgrade():
    postgres = op.get_bind().dialect.name == "postgresql"
    consumers = "('project_management.accounting_outcomes.v1','project_management.accounting_quarantine.v1')"
    fields = (
        "tenant_id",
        "organization_id",
        "consumer_name",
        "event_id",
        "envelope_json",
        "envelope_hash",
        "deduplication_key",
    )
    comparison = " OR ".join(
        f"NEW.{field} IS DISTINCT FROM OLD.{field}"
        if postgres
        else f"NEW.{field} IS NOT OLD.{field}"
        for field in fields
    )
    if postgres:
        op.execute(f"""
        CREATE FUNCTION guard_accounting_inbound_evidence() RETURNS trigger AS $$
        BEGIN
          IF OLD.consumer_name IN {consumers} THEN
            IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'Accounting inbound evidence is immutable'; END IF;
            IF OLD.consumer_name = 'project_management.accounting_quarantine.v1' OR {comparison} THEN
              RAISE EXCEPTION 'Accounting inbound evidence is immutable';
            END IF;
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_accounting_inbound_evidence BEFORE UPDATE OR DELETE ON project_finance_inbox_receipts
        FOR EACH ROW EXECUTE FUNCTION guard_accounting_inbound_evidence();
        CREATE FUNCTION guard_accounting_business_evidence() RETURNS trigger AS $$
        BEGIN
          IF OLD.external_system = 'external_accounting' THEN RAISE EXCEPTION 'Accounting business evidence is immutable'; END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END; $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_accounting_business_evidence BEFORE UPDATE OR DELETE ON project_billing_external_events
        FOR EACH ROW EXECUTE FUNCTION guard_accounting_business_evidence();
        """)
    else:
        op.execute(f"""CREATE TRIGGER trg_accounting_inbound_evidence_update BEFORE UPDATE ON project_finance_inbox_receipts
        WHEN OLD.consumer_name IN {consumers} AND (OLD.consumer_name = 'project_management.accounting_quarantine.v1' OR {comparison})
        BEGIN SELECT RAISE(ABORT, 'Accounting inbound evidence is immutable'); END""")
        op.execute(f"""CREATE TRIGGER trg_accounting_inbound_evidence_delete BEFORE DELETE ON project_finance_inbox_receipts
        WHEN OLD.consumer_name IN {consumers}
        BEGIN SELECT RAISE(ABORT, 'Accounting inbound evidence is immutable'); END""")
        for operation in ("UPDATE", "DELETE"):
            op.execute(f"""CREATE TRIGGER trg_accounting_business_evidence_{operation.lower()} BEFORE {operation} ON project_billing_external_events
            WHEN OLD.external_system = 'external_accounting'
            BEGIN SELECT RAISE(ABORT, 'Accounting business evidence is immutable'); END""")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER trg_accounting_inbound_evidence ON project_finance_inbox_receipts"
        )
        op.execute(
            "DROP TRIGGER trg_accounting_business_evidence ON project_billing_external_events"
        )
        op.execute("DROP FUNCTION guard_accounting_inbound_evidence()")
        op.execute("DROP FUNCTION guard_accounting_business_evidence()")
    else:
        for name in ("inbound", "business"):
            for operation in ("update", "delete"):
                op.execute(f"DROP TRIGGER trg_accounting_{name}_evidence_{operation}")
