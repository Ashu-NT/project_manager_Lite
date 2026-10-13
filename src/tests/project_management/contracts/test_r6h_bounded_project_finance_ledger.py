from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import event

from src.core.modules.project_management.contracts.reads.financials.models.project_finance_ledger_query import (
    ProjectFinanceLedgerQuery,
)
from src.tests.project_management.contracts.test_project_finance_canonical_read_models import (
    _approved_controls,
    _clone_posted_entry,
)


@pytest.mark.parametrize("count", [0, 1, 24, 25, 100, 1001])
def test_ledger_sql_pages_preserve_full_control_totals_and_exact_traversal(services, count):
    project, _, _, entry, _ = _approved_controls(services)
    session = services["session"]
    for _ in range(count):
        _clone_posted_entry(session, entry.id, amount="0.01", posted_on=date(2026, 8, 5))
    _clone_posted_entry(session, entry.id, amount="999.99", posted_on=date(2026, 9, 1))
    session.commit()
    reader = services["finance_service"]._finance_snapshot_reader
    scope = services["tenant_context_service"].require_active_scope_ids(operation_label="test")
    params = dict(tenant_id=scope.tenant_id, organization_id=scope.organization_id,
                  project_id=project.id, as_of=date(2026, 8, 31))
    statements = []

    def record(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(session.bind, "before_cursor_execute", record)
    try:
        first = reader.read_facts(**params, ledger_query=ProjectFinanceLedgerQuery(limit=25))
    finally:
        event.remove(session.bind, "before_cursor_execute", record)
    assert len(first.ledger_entries) == min(25, count + 2)
    assert first.ledger_total == count + 2
    assert first.control.posted_actual == Decimal(25) + count * Decimal("0.01")
    assert first.control.forecast_etc == Decimal(80)
    assert len(first.cost_aggregates) == 2
    assert len(first.actual_months) == 1
    # Fixed query count and fixed detail hydration irrespective of ledger size.
    assert len(statements) == 9
    assert sum("LIMIT" in sql and "project_finance_ledger" in sql and "OFFSET" in sql for sql in statements) >= 1
    rows = list(first.ledger_entries)
    for offset in range(25, first.ledger_total, 25):
        page = reader.read_facts(**params, ledger_query=ProjectFinanceLedgerQuery(offset=offset, limit=25))
        assert page.control == first.control
        assert page.cost_aggregates == first.cost_aggregates
        assert page.ledger_total == first.ledger_total
        rows.extend(page.ledger_entries)
    identities = [(row.reference_type, row.fact_id) for row in rows]
    assert len(set(identities)) == len(rows) == first.ledger_total
    assert sum((row.amount for row in rows if row.stage == "actual"), Decimal(0)) == first.control.posted_actual
    assert [row.fact_id for row in rows if row.stage == "actual"] == sorted(row.fact_id for row in rows if row.stage == "actual")
    empty = reader.read_facts(**params, ledger_query=ProjectFinanceLedgerQuery(offset=first.ledger_total, limit=25))
    assert empty.ledger_entries == ()
    assert empty.control == first.control
    assert empty.ledger_total == first.ledger_total
    snapshot = services["finance_service"].get_finance_export_snapshot(
        project.id, as_of=params["as_of"], ledger_query=ProjectFinanceLedgerQuery(offset=1, limit=1))
    assert len(snapshot.ledger) == 1
    assert snapshot.ledger_total == first.ledger_total
    assert snapshot.actual == first.control.posted_actual
    assert snapshot.reconciliation.is_reconciled
