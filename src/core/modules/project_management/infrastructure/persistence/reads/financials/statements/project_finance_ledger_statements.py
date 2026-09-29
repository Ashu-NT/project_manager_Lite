"""One scoped ledger relation for detail pages and full-set SQL aggregates."""

from datetime import date

from sqlalchemy import Date, String, case, cast, func, literal, select, union_all

from .finance_amount_expressions import (
    actual_amount_expression,
    commitment_amount_expression,
)
from .finance_snapshot_statements import (
    actual_cost_facts_statement,
    approved_forecast_line_facts_statement,
    commitment_facts_statement,
    planned_cost_facts_statement,
)


def project_finance_ledger_relation(*, tenant_id, organization_id, project_id, as_of,
                            project_currency, forecast_id):
    scope = dict(tenant_id=tenant_id, organization_id=organization_id, project_id=project_id)
    timed = dict(**scope, as_of=as_of)
    planned = planned_cost_facts_statement(**timed).order_by(None).subquery()
    actual = actual_cost_facts_statement(**timed).order_by(None).subquery()
    commitment = commitment_facts_statement(**timed).order_by(None).subquery()
    forecast = approved_forecast_line_facts_statement(
        **scope, forecast_id=forecast_id
    ).order_by(None).subquery()
    actual_amount, actual_matches = actual_amount_expression(actual.c, project_currency)
    commitment_amount, commitment_matches = commitment_amount_expression(commitment.c, project_currency)

    def project(source, *, source_key, source_label, reference_type, cost_type, stage,
                amount, currency_matches, occurred_on, description, **optional):
        columns = dict(
            fact_id=source.c.id, task_id=source.c.task_id,
            resource_id=cast(literal(None), String), description=description,
            source_key=source_key, source_label=source_label,
            reference_type=literal(reference_type), cost_type=cost_type,
            stage=literal(stage), currency_code=literal(project_currency),
            amount=amount, occurred_on=occurred_on, cost_code_id=source.c.cost_code_id,
            source_type=func.lower(source_key),
            financial_period_id=cast(literal(None), String),
            period_start=cast(literal(None), Date), period_end=cast(literal(None), Date),
            currency_mismatch_count=case((currency_matches, 0), else_=1),
        )
        columns.update(optional)
        return select(*(value.label(key) for key, value in columns.items())).select_from(source)

    return union_all(
        project(planned, source_key=literal("PLANNED_COST"), source_label=literal("Planned Cost"),
                reference_type="planned_cost_line", cost_type=literal("LABOR"), stage="planned",
                amount=planned.c.amount, currency_matches=func.upper(planned.c.currency_code) == project_currency,
                occurred_on=planned.c.as_of, description=literal("Assignment ") + planned.c.source_assignment_id,
                resource_id=planned.c.resource_id),
        project(forecast, source_key=literal("APPROVED_FORECAST"), source_label=literal("Approved Forecast ETC"),
                reference_type="forecast_line", cost_type=literal("OTHER"), stage="forecast",
                amount=forecast.c.amount, currency_matches=func.upper(forecast.c.currency_code) == project_currency,
                occurred_on=func.coalesce(forecast.c.period_start, forecast.c.as_of_date),
                description=forecast.c.description, source_type=forecast.c.source_type,
                period_start=forecast.c.period_start, period_end=forecast.c.period_end),
        project(commitment, source_key=literal("PROCUREMENT_COMMITMENT"), source_label=literal("Procurement Commitment"),
                reference_type="commitment_line", cost_type=literal("MATERIAL"), stage="committed",
                amount=commitment_amount, currency_matches=commitment_matches,
                occurred_on=commitment.c.order_date,
                description=literal("Purchase order line ") + commitment.c.purchase_order_line_id,
                source_type=literal("open_commitment")),
        project(actual, source_key=actual.c.source_key,
                source_label=case((actual.c.source_key == "APPROVED_TIME", "Approved Time"),
                                  (actual.c.source_key == "PROCUREMENT_ACTUAL", "Procurement Actual"),
                                  else_="Manual Actual"),
                reference_type="cost_entry", cost_type=actual.c.cost_type, stage="actual",
                amount=actual_amount, currency_matches=actual_matches,
                occurred_on=actual.c.posting_date, description=actual.c.description,
                resource_id=actual.c.resource_id, financial_period_id=actual.c.financial_period_id),
    ).subquery("project_finance_ledger")


def ledger_aggregates_statement(ledger):
    dimensions = [ledger.c.stage, ledger.c.cost_type, ledger.c.currency_code,
                  ledger.c.source_key, ledger.c.source_label]
    return select(
        *dimensions, func.sum(ledger.c.amount).label("total_amount"),
        func.count().label("row_count"),
        func.sum(ledger.c.currency_mismatch_count).label("currency_mismatch_count"),
    ).group_by(*dimensions).order_by(*dimensions)


def visible_ledger_relation(ledger, *, include_sensitive: bool, as_of: date):
    if include_sensitive:
        return ledger
    # Redact/group before counting and paging, never aggregate only a page.
    group = [ledger.c.source_key, ledger.c.source_label, ledger.c.stage, ledger.c.currency_code]
    replacements = dict(
        fact_id=literal("restricted:") + ledger.c.source_key + literal(":") + ledger.c.stage,
        task_id=cast(literal(None), String), resource_id=cast(literal(None), String),
        description=literal("Restricted labor cost"), reference_type=literal("restricted_finance"),
        amount=func.sum(ledger.c.amount), occurred_on=literal(as_of),
        cost_code_id=cast(literal(None), String), source_type=literal("restricted"),
        financial_period_id=cast(literal(None), String),
        period_start=cast(literal(None), Date), period_end=cast(literal(None), Date),
        currency_mismatch_count=func.sum(ledger.c.currency_mismatch_count),
        cost_type=literal("LABOR"),
    )
    restricted = select(*(
        replacements.get(column.key, column).label(column.key) for column in ledger.c
    )).where(ledger.c.cost_type == "LABOR").group_by(*group)
    return union_all(select(ledger).where(ledger.c.cost_type != "LABOR"), restricted).subquery("visible_ledger")


def ledger_page_statement(ledger, query):
    return select(ledger).order_by(
        func.coalesce(ledger.c.occurred_on, literal(date.min)), ledger.c.source_key,
        ledger.c.stage, func.lower(ledger.c.description), ledger.c.reference_type, ledger.c.fact_id,
    ).offset(query.offset).limit(query.limit)
