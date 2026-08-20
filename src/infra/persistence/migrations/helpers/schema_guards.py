"""Database-enforced immutable ledger guards required by the initial schema."""

from __future__ import annotations

from typing import Any


_COST_ENTRY_COLUMNS = (
    "tenant_id", "organization_id", "project_id", "description", "entry_kind",
    "amount", "currency_code", "base_amount", "base_currency_code", "exchange_rate",
    "exchange_rate_date", "exchange_rate_source", "exchange_rate_captured_at",
    "transaction_date", "posting_date", "financial_period_id", "cost_code_id",
    "task_id", "resource_id", "source_module", "source_type", "source_id",
    "source_line_id", "source_revision", "source_content_hash", "posting_purpose",
    "idempotency_key", "reverses_entry_id", "created_by", "created_at",
    "submitted_by", "submitted_at", "approved_by", "approved_at", "posted_by",
    "posted_at",
)
_IMMUTABLE_LEDGER_TABLES = (
    "project_commitment_source_revisions",
    "project_commitment_matches",
    "project_approved_time_labor_postings",
)
_ENVELOPE_TABLES = (
    "platform_time_financial_outbox",
    "inventory_procurement_financial_outbox",
    "project_finance_inbox_receipts",
)
_ENVELOPE_COLUMNS = (
    "id", "tenant_id", "organization_id", "event_id", "event_type",
    "aggregate_type", "aggregate_id", "aggregate_version", "occurred_at",
    "envelope_json", "envelope_hash", "created_at",
)


def _install_cost_entry_guards(operations: Any, dialect: str) -> None:
    table = "project_cost_entries"
    if dialect == "postgresql":
        comparisons = " OR ".join(
            f"OLD.{column} IS DISTINCT FROM NEW.{column}" for column in _COST_ENTRY_COLUMNS
        )
        operations.execute(
            f"""CREATE FUNCTION prevent_project_cost_entry_mutation() RETURNS trigger AS $$
            BEGIN
                IF OLD.status IN ('posted', 'reversed') AND (
                    ({comparisons})
                    OR (OLD.status = 'reversed' AND NEW.status <> 'reversed')
                    OR (OLD.status = 'posted' AND NEW.status NOT IN ('posted', 'reversed'))
                ) THEN
                    RAISE EXCEPTION 'posted project cost entry financial facts are immutable';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql"""
        )
        operations.execute(
            f"CREATE TRIGGER trg_project_cost_entries_immutable_update BEFORE UPDATE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_project_cost_entry_mutation()"
        )
        operations.execute(
            """CREATE FUNCTION prevent_project_cost_entry_delete() RETURNS trigger AS $$
            BEGIN
                IF OLD.status IN ('posted', 'reversed') THEN
                    RAISE EXCEPTION 'posted project cost entries cannot be deleted';
                END IF;
                RETURN OLD;
            END;
            $$ LANGUAGE plpgsql"""
        )
        operations.execute(
            f"CREATE TRIGGER trg_project_cost_entries_immutable_delete BEFORE DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_project_cost_entry_delete()"
        )
    elif dialect == "sqlite":
        comparisons = " OR ".join(
            f"OLD.{column} IS NOT NEW.{column}" for column in _COST_ENTRY_COLUMNS
        )
        operations.execute(
            f"""CREATE TRIGGER trg_project_cost_entries_immutable_update
            BEFORE UPDATE ON {table}
            WHEN OLD.status IN ('posted', 'reversed') AND (
                ({comparisons})
                OR (OLD.status = 'reversed' AND NEW.status <> 'reversed')
                OR (OLD.status = 'posted' AND NEW.status NOT IN ('posted', 'reversed'))
            )
            BEGIN
                SELECT RAISE(ABORT, 'posted project cost entry financial facts are immutable');
            END"""
        )
        operations.execute(
            f"""CREATE TRIGGER trg_project_cost_entries_immutable_delete
            BEFORE DELETE ON {table}
            WHEN OLD.status IN ('posted', 'reversed')
            BEGIN
                SELECT RAISE(ABORT, 'posted project cost entries cannot be deleted');
            END"""
        )


def _install_immutable_ledger_guards(operations: Any, dialect: str) -> None:
    for table in _IMMUTABLE_LEDGER_TABLES:
        if dialect == "postgresql":
            function = f"prevent_{table}_mutation"
            operations.execute(
                f"CREATE FUNCTION {function}() RETURNS trigger AS $$ BEGIN "
                f"RAISE EXCEPTION '{table} rows are immutable'; END; $$ LANGUAGE plpgsql"
            )
            operations.execute(
                f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {function}()"
            )
        elif dialect == "sqlite":
            for operation in ("UPDATE", "DELETE"):
                operations.execute(
                    f"CREATE TRIGGER trg_{table}_immutable_{operation.lower()} "
                    f"BEFORE {operation} ON {table} BEGIN SELECT RAISE(ABORT, "
                    f"'{table} rows are immutable'); END"
                )


def _install_envelope_guards(operations: Any, dialect: str) -> None:
    for table in _ENVELOPE_TABLES:
        if dialect == "postgresql":
            function = f"protect_{table}_envelope"
            comparisons = " OR ".join(
                f"OLD.{column} IS DISTINCT FROM NEW.{column}" for column in _ENVELOPE_COLUMNS
            )
            operations.execute(
                f"CREATE FUNCTION {function}() RETURNS trigger AS $$ BEGIN IF {comparisons} "
                f"THEN RAISE EXCEPTION '{table} envelope columns are immutable'; "
                "END IF; RETURN NEW; END; $$ LANGUAGE plpgsql"
            )
            operations.execute(
                f"CREATE TRIGGER trg_{table}_envelope_immutable BEFORE UPDATE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {function}()"
            )
        elif dialect == "sqlite":
            comparisons = " OR ".join(
                f"OLD.{column} IS NOT NEW.{column}" for column in _ENVELOPE_COLUMNS
            )
            operations.execute(
                f"CREATE TRIGGER trg_{table}_envelope_immutable BEFORE UPDATE ON {table} "
                f"WHEN {comparisons} BEGIN SELECT RAISE(ABORT, "
                f"'{table} envelope columns are immutable'); END"
            )


def install_database_guards(operations: Any, bind: Any) -> None:
    dialect = bind.dialect.name
    _install_cost_entry_guards(operations, dialect)
    _install_immutable_ledger_guards(operations, dialect)
    _install_envelope_guards(operations, dialect)


def remove_database_guards(operations: Any, bind: Any) -> None:
    dialect = bind.dialect.name
    for table in reversed(_ENVELOPE_TABLES):
        operations.execute(f"DROP TRIGGER IF EXISTS trg_{table}_envelope_immutable")
        if dialect == "postgresql":
            operations.execute(f"DROP FUNCTION IF EXISTS protect_{table}_envelope()")
    for table in reversed(_IMMUTABLE_LEDGER_TABLES):
        if dialect == "postgresql":
            operations.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
            operations.execute(f"DROP FUNCTION IF EXISTS prevent_{table}_mutation()")
        elif dialect == "sqlite":
            operations.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_update")
            operations.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_delete")
    operations.execute("DROP TRIGGER IF EXISTS trg_project_cost_entries_immutable_delete")
    operations.execute("DROP TRIGGER IF EXISTS trg_project_cost_entries_immutable_update")
    if dialect == "postgresql":
        operations.execute("DROP FUNCTION IF EXISTS prevent_project_cost_entry_delete()")
        operations.execute("DROP FUNCTION IF EXISTS prevent_project_cost_entry_mutation()")


__all__ = ["install_database_guards", "remove_database_guards"]
