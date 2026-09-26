"""One runtime-role proof over the R6D Rate, Actual, Time, and Commitment surface."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from src.core.platform.domain.finance import DecimalQuantityPayload, MonetaryRatePayload
from src.core.platform.integration import (
    PROCUREMENT_COMMITMENT_EVENT_TYPE,
    PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE,
    ProcurementCommitmentEventPayload,
    ProcurementReceiptAccrualEventPayload,
)
from src.infra.persistence.db.postgresql_rls import validate_postgresql_execution_role
from src.tests.integration.postgresql import (
    test_r6d_d_approved_time_labor_posting as time_case,
)
from src.tests.integration.postgresql import (
    test_r6d_e_commitment_projection as procurement_case,
)

pytestmark = pytest.mark.postgresql_integration

_TIME_TABLES = (
    "project_finance_rate_cards",
    "project_finance_rate_card_lines",
    "project_cost_entries",
    "project_approved_time_labor_postings",
)
_PROCUREMENT_TABLES = (
    "project_commitments",
    "project_commitment_lines",
    "project_commitment_source_revisions",
    "project_commitment_matches",
)
_INBOX = "project_finance_inbox_receipts"
_TABLES = (*_TIME_TABLES, *_PROCUREMENT_TABLES, _INBOX)
_TRIGGER_IMMUTABLE_UPDATES = {
    "project_approved_time_labor_postings",
    "project_commitment_source_revisions",
    "project_commitment_matches",
    _INBOX,
}
_UNIQUE_FIELDS = {
    "project_finance_rate_cards": {"name": "R6D-F hostile card"},
    "project_finance_rate_card_lines": {},
    "project_cost_entries": {
        "source_id": "r6df-hostile-source",
        "idempotency_key": "r6df-hostile-actual-idempotency",
    },
    "project_approved_time_labor_postings": {
        "time_entry_id": "r6df-hostile-time-entry",
        "approved_snapshot_id": "r6df-hostile-snapshot",
        "source_event_id": "r6df-hostile-time-event",
    },
    "project_commitments": {"purchase_order_id": "r6df-hostile-po"},
    "project_commitment_lines": {
        "purchase_order_line_id": "r6df-hostile-po-line",
        "source_idempotency_key": "r6df-hostile-line-idempotency",
    },
    "project_commitment_source_revisions": {
        "source_idempotency_key": "r6df-hostile-revision-idempotency",
    },
    "project_commitment_matches": {
        "idempotency_key": "r6df-hostile-match-idempotency",
    },
    _INBOX: {
        "event_id": "r6df-hostile-inbox-event",
        "deduplication_key": "r6df-hostile-inbox-dedupe",
    },
}


def _clone_statement(table: str, changes: dict[str, str]) -> tuple[str, dict[str, str]]:
    assert table in _TABLES or table in {
        "project_finance_cost_codes", "resources", "tasks", "sites", "parties"
    }
    values = []
    parameters = {}
    for index, (column, value) in enumerate(changes.items()):
        key = f"value_{index}"
        values.extend((f"'{column}'", f"CAST(:{key} AS text)"))
        parameters[key] = value
    statement = (
        f"INSERT INTO {table} SELECT "
        f"(jsonb_populate_record(NULL::{table}, to_jsonb(source) || "
        f"jsonb_build_object({', '.join(values)}))).* "
        f"FROM {table} AS source WHERE source.id=:source_id"
    )
    return statement, parameters


def _clone(connection, table: str, source_id: str, changes: dict[str, str]) -> None:
    statement, parameters = _clone_statement(table, changes)
    result = connection.execute(text(statement), {**parameters, "source_id": source_id})
    assert result.rowcount == 1


def _id(connection, table: str, predicate: str, **parameters) -> str:
    assert table in _TABLES
    value = connection.scalar(text(f"SELECT id FROM {table} WHERE {predicate} LIMIT 1"), parameters)
    assert value is not None, (table, predicate)
    return str(value)


def _must_reject(
    session, statement: str, parameters: dict, *, sqlstate: str | tuple[str, ...]
) -> None:
    try:
        session.execute(text(statement), parameters)
    except DBAPIError as exc:
        session.rollback()
        expected = (sqlstate,) if isinstance(sqlstate, str) else sqlstate
        assert exc.orig.sqlstate in expected, (statement, exc.orig.sqlstate)
    else:
        session.rollback()
        pytest.fail(f"Hostile SQL unexpectedly succeeded: {statement}")


def _seed_scopes(environment) -> None:
    with environment.admin_engine.connect() as connection:
        time_exists = connection.scalar(text(
            "SELECT EXISTS (SELECT 1 FROM tenants WHERE id=:id)"
        ), {"id": time_case.TENANT_A})
        procurement_exists = connection.scalar(text(
            "SELECT EXISTS (SELECT 1 FROM tenants WHERE id=:id)"
        ), {"id": procurement_case.TENANT_A})
    if not time_exists:
        time_case.seed_approved_time_scope(environment)
    if not procurement_exists:
        procurement_case.seed_procurement_scope(environment)


def _deliver_legal_paths(environment) -> None:
    rate_line_id = "r6df-rls-governed-rate-line"
    time_case._seed_rate_race_line(
        environment,
        resource_id="r6df-rls-governed-resource",
        line_id=rate_line_id,
        code="R6DF-RLS-GOVERNED",
    )
    boundary = time_case._governed_rate_boundary(environment)
    changed = boundary.rate_card(lambda service: service.update_line(
        rate_line_id, expected_version=1, rate_amount=Decimal("44.125")
    ))
    assert changed.version == 2 and changed.rate_amount == Decimal("44.125")
    manual = boundary.cost_entry(lambda service: service.create_manual_entry(
        project_id=time_case.PROJECT_A,
        command_id="r6df-rls-legal-manual",
        description="Same-scope manual Actual probe",
        amount=Decimal(25), currency_code="USD",
        transaction_date=date(2026, 9, 10),
        cost_code_id=time_case.COST_CODE_A,
        resource_id=time_case.RESOURCE_A,
    ))
    assert manual.status.value == "draft"

    source, outbox, worker = time_case._build_dispatcher(environment)
    try:
        outbox.enqueue(time_case._approved_time_envelope("combined-rls"))
        source.commit()
        assert worker.dispatch_pending(limit=1) == 1
    finally:
        source.close()

    source, outbox, worker = procurement_case._dispatcher(environment)
    try:
        commitment = ProcurementCommitmentEventPayload(
            project_id=procurement_case.PROJECT_A,
            purchase_order_id="r6df-rls-po",
            purchase_order_line_id="r6df-rls-line",
            purchase_order_number="R6DF-RLS",
            supplier_party_id=procurement_case.SUPPLIER_A,
            site_id=procurement_case.SITE_A,
            state="SENT", source_revision=1, source_content_hash="a" * 64,
            ordered_quantity=DecimalQuantityPayload(value="10", unit="EA"),
            unit_price=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
            order_date=date(2026, 9, 10),
        )
        outbox.enqueue(procurement_case._event(
            PROCUREMENT_COMMITMENT_EVENT_TYPE, commitment,
            event_id="r6df-rls-commit-event", aggregate_id="r6df-rls-line",
        ))
        source.commit()
        assert worker.dispatch_pending(limit=1) == 1
        receipt = ProcurementReceiptAccrualEventPayload(
            project_id=procurement_case.PROJECT_A,
            receipt_id="r6df-rls-receipt",
            receipt_line_id="r6df-rls-receipt-line",
            receipt_number="R6DF-RLS-REC",
            purchase_order_id="r6df-rls-po",
            purchase_order_line_id="r6df-rls-line",
            supplier_party_id=procurement_case.SUPPLIER_A,
            site_id=procurement_case.SITE_A,
            source_revision=1, source_content_hash="b" * 64,
            posted_at=datetime(2026, 9, 10, tzinfo=timezone.utc),
            accepted_quantity=DecimalQuantityPayload(value="4", unit="EA"),
            unit_cost=MonetaryRatePayload(amount="10", currency="USD", per_unit="EA"),
        )
        outbox.enqueue(procurement_case._event(
            PROCUREMENT_RECEIPT_ACCRUAL_EVENT_TYPE, receipt,
            event_id="r6df-rls-receipt-event", aggregate_id="r6df-rls-receipt-line",
        ))
        source.commit()
        assert worker.dispatch_pending(limit=1) == 1
    finally:
        source.close()


def _seed_foreign_parents(
    environment, ids: dict[str, str], procurement_actual: str
) -> None:
    with environment.admin_engine.begin() as connection:
        _clone(connection, "project_cost_entries", procurement_actual, {
            "id": "r6df-local-extra-actual",
            "source_id": "r6df-local-extra-source",
            "source_line_id": "r6df-local-extra-line",
            "idempotency_key": "r6df-local-extra-idem",
        })
        connection.execute(text(
            "INSERT INTO project_cost_entries SELECT "
            "(jsonb_populate_record(NULL::project_cost_entries, to_jsonb(c) || "
            "jsonb_build_object('id', 'r6df-rls-draft-actual', "
            "'source_id', 'r6df-rls-draft-source', "
            "'idempotency_key', 'r6df-rls-draft-idem', 'status', 'draft', "
            "'base_amount', NULL, 'base_currency_code', NULL, "
            "'exchange_rate', NULL, 'exchange_rate_date', NULL, "
            "'exchange_rate_source', NULL, 'exchange_rate_captured_at', NULL, "
            "'posting_date', NULL, 'financial_period_id', NULL, "
            "'posted_by', NULL, 'posted_at', NULL))).* "
            "FROM project_cost_entries c WHERE c.id=:source_id"
        ), {"source_id": ids["project_cost_entries"]})
        _clone(connection, "project_finance_rate_cards", ids["project_finance_rate_cards"], {
            "id": "r6df-foreign-rate-card", "tenant_id": time_case.TENANT_B,
            "organization_id": time_case.ORG_B, "project_id": time_case.PROJECT_B,
            "name": "R6D-F foreign rate",
        })
        for table, source, new_id, code_field, code in (
            ("project_finance_cost_codes", time_case.COST_CODE_A,
             "r6df-foreign-cost-code", "code", "R6DF-FOREIGN"),
            ("resources", time_case.RESOURCE_A,
             "r6df-foreign-resource", "resource_code", "R6DF-FOREIGN"),
            ("tasks", time_case.TASK_A,
             "r6df-foreign-task", "task_code", "R6DF-FOREIGN"),
        ):
            changes = {"id": new_id, code_field: code}
            if table == "tasks":
                changes["project_id"] = time_case.PROJECT_B
            else:
                changes.update(tenant_id=time_case.TENANT_B,
                               organization_id=time_case.ORG_B)
            _clone(connection, table, source, changes)
        _clone(connection, "project_finance_cost_codes", procurement_case.COST_CODE_A, {
            "id": "r6df-proc-foreign-cost", "tenant_id": procurement_case.TENANT_B,
            "organization_id": procurement_case.ORG_B, "code": "R6DF-FOREIGN",
        })
        for table, source, new_id, code_field in (
            ("sites", procurement_case.SITE_A, "r6df-foreign-site", "site_code"),
            ("parties", procurement_case.SUPPLIER_A, "r6df-foreign-party", "party_code"),
        ):
            _clone(connection, table, source, {
                "id": new_id, "tenant_id": procurement_case.TENANT_B,
                "organization_id": procurement_case.ORG_B,
                code_field: "R6DF-FOREIGN",
            })
        _clone(connection, "project_commitments", ids["project_commitments"], {
            "id": "r6df-foreign-commitment",
            "tenant_id": procurement_case.TENANT_B,
            "organization_id": procurement_case.ORG_B,
            "project_id": procurement_case.PROJECT_B,
            "purchase_order_id": "r6df-foreign-po",
            "supplier_party_id": "r6df-foreign-party",
            "site_id": "r6df-foreign-site",
        })
        _clone(connection, "project_commitment_lines", ids["project_commitment_lines"], {
            "id": "r6df-foreign-commitment-line",
            "tenant_id": procurement_case.TENANT_B,
            "organization_id": procurement_case.ORG_B,
            "project_id": procurement_case.PROJECT_B,
            "commitment_id": "r6df-foreign-commitment",
            "purchase_order_line_id": "r6df-foreign-po-line",
            "cost_code_id": "r6df-proc-foreign-cost",
            "source_idempotency_key": "r6df-foreign-line-idem",
        })


def test_combined_finance_runtime_role_rls_and_scoped_parent_denials(
    postgres_test_environment,
):
    environment = postgres_test_environment
    _seed_scopes(environment)
    _deliver_legal_paths(environment)
    with environment.admin_engine.connect() as connection:
        role = connection.execute(text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='app_runtime'"
        )).one()
        assert role.rolsuper is False and role.rolbypassrls is False
        for table in _TABLES:
            owner, enabled, forced = connection.execute(text(
                "SELECT pg_get_userbyid(relowner), relrowsecurity, relforcerowsecurity "
                "FROM pg_class WHERE relname=:table"
            ), {"table": table}).one()
            assert owner != "app_runtime" and enabled and forced, table
        ids = {
            "project_finance_rate_cards": time_case.RATE_CARD_A,
            "project_finance_rate_card_lines": time_case.RATE_LINE_A,
            "project_cost_entries": _id(connection, "project_cost_entries",
                "project_id=:project AND source_module='platform_time'",
                project=time_case.PROJECT_A),
            "project_approved_time_labor_postings": _id(connection,
                "project_approved_time_labor_postings", "project_id=:project",
                project=time_case.PROJECT_A),
            "project_commitments": _id(connection, "project_commitments",
                "purchase_order_id='r6df-rls-po'"),
            "project_commitment_lines": _id(connection, "project_commitment_lines",
                "purchase_order_line_id='r6df-rls-line'"),
            "project_commitment_source_revisions": _id(connection,
                "project_commitment_source_revisions", "project_id=:project",
                project=procurement_case.PROJECT_A),
            "project_commitment_matches": _id(connection,
                "project_commitment_matches", "project_id=:project",
                project=procurement_case.PROJECT_A),
            _INBOX: _id(connection, _INBOX, "event_id='r6df-rls-receipt-event'"),
        }
        procurement_actual = _id(connection, "project_cost_entries",
            "project_id=:project AND source_module='inventory_procurement'",
            project=procurement_case.PROJECT_A)
    _seed_foreign_parents(environment, ids, procurement_actual)

    for table in _TABLES:
        tenant, organization = (
            (time_case.TENANT_A, time_case.ORG_A)
            if table in _TIME_TABLES else
            (procurement_case.TENANT_A, procurement_case.ORG_A)
        )
        foreign_tenant, foreign_organization = (
            (time_case.TENANT_B, time_case.ORG_B)
            if table in _TIME_TABLES else
            (procurement_case.TENANT_B, procurement_case.ORG_B)
        )
        local = environment.runtime_session(
            tenant_id=tenant, organization_id=organization
        )
        foreign = environment.runtime_session(
            tenant_id=foreign_tenant, organization_id=foreign_organization
        )
        wrong_org = environment.runtime_session(
            tenant_id=tenant, organization_id=foreign_organization
        )
        try:
            validate_postgresql_execution_role(local)
            validate_postgresql_execution_role(foreign)
            assert local.scalar(text(f"SELECT count(*) FROM {table} WHERE id=:id"),
                                {"id": ids[table]}) == 1
            for outsider in (foreign, wrong_org):
                assert outsider.scalar(text(f"SELECT count(*) FROM {table} WHERE id=:id"),
                                       {"id": ids[table]}) == 0
                assert outsider.execute(text(f"DELETE FROM {table} WHERE id=:id"),
                                        {"id": ids[table]}).rowcount == 0
                outsider.rollback()
            update_id = (
                "r6df-rls-draft-actual" if table == "project_cost_entries"
                else ids[table]
            )
            update_denial = (
                "P0001" if table in _TRIGGER_IMMUTABLE_UPDATES else "42501"
            )
            _must_reject(local, f"UPDATE {table} SET tenant_id=:foreign WHERE id=:id",
                         {"foreign": foreign_tenant, "id": update_id},
                         sqlstate=update_denial)
            _must_reject(local, f"UPDATE {table} SET organization_id=:foreign WHERE id=:id",
                         {"foreign": foreign_organization, "id": update_id},
                         sqlstate=update_denial)
            changes = {
                "id": f"r6df-hostile-{table}",
                "tenant_id": foreign_tenant,
                "organization_id": foreign_organization,
                **_UNIQUE_FIELDS[table],
            }
            statement, parameters = _clone_statement(table, changes)
            _must_reject(local, statement,
                         {**parameters, "source_id": ids[table]}, sqlstate="42501")
        finally:
            local.close()
            foreign.close()
            wrong_org.close()

    # Scoped FKs, not RLS, reject in-scope rows pointing at genuine foreign parents.
    parent_attacks = (
        ("project_finance_rate_cards", "project_id", time_case.PROJECT_B),
        ("project_finance_rate_card_lines", "rate_card_id", "r6df-foreign-rate-card"),
        ("project_cost_entries", "project_id", time_case.PROJECT_B),
        ("project_cost_entries", "cost_code_id", procurement_case.COST_CODE_A),
        ("project_cost_entries", "task_id", "r6df-foreign-task"),
        ("project_cost_entries", "resource_id", "r6df-foreign-resource"),
        ("project_cost_entries", "reverses_entry_id", procurement_actual),
        ("project_approved_time_labor_postings", "project_id", time_case.PROJECT_B),
        ("project_approved_time_labor_postings", "actual_cost_entry_id", procurement_actual),
        ("project_commitments", "project_id", procurement_case.PROJECT_B),
        ("project_commitment_lines", "commitment_id", "r6df-foreign-commitment"),
        ("project_commitment_source_revisions", "commitment_line_id",
         "r6df-foreign-commitment-line"),
        ("project_commitment_matches", "commitment_line_id",
         "r6df-foreign-commitment-line"),
        ("project_commitment_matches", "cost_entry_id", ids["project_cost_entries"]),
        (_INBOX, "source_project_id", procurement_case.PROJECT_B),
    )
    for index, (table, column, foreign_id) in enumerate(parent_attacks):
        tenant, organization = (
            (time_case.TENANT_A, time_case.ORG_A)
            if table in _TIME_TABLES else
            (procurement_case.TENANT_A, procurement_case.ORG_A)
        )
        local = environment.runtime_session(
            tenant_id=tenant, organization_id=organization
        )
        try:
            changes = {
                "id": f"r6df-parent-attack-{index}",
                **_UNIQUE_FIELDS[table], column: foreign_id,
            }
            if column == "reverses_entry_id":
                changes.update(entry_kind="reversal", amount="-10", base_amount="-10")
            if table == "project_commitment_matches" and column == "commitment_line_id":
                changes["cost_entry_id"] = "r6df-local-extra-actual"
            statement, parameters = _clone_statement(table, changes)
            _must_reject(local, statement,
                         {**parameters, "source_id": ids[table]}, sqlstate="23503")
        finally:
            local.close()
