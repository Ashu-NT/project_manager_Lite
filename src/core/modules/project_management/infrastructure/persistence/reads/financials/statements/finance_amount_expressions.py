"""Shared project-currency expressions for ledger and aggregate projections."""

from sqlalchemy import and_, case, func, or_


def actual_amount_expression(source, project_currency: str):
    transaction_matches = func.upper(source.currency_code) == project_currency
    base_matches = and_(
        func.upper(source.base_currency_code) == project_currency,
        source.base_amount.is_not(None),
    )
    return (
        case(
            (transaction_matches, source.amount),
            (base_matches, source.base_amount),
            else_=0,
        ),
        or_(transaction_matches, base_matches),
    )


def commitment_amount_expression(source, project_currency: str):
    transaction_matches = func.upper(source.currency_code) == project_currency
    base_matches = func.upper(source.base_currency_code) == project_currency
    transaction_remaining = source.amount - source.matched_amount
    base_remaining = source.base_amount - source.matched_amount * source.exchange_rate
    return (
        case(
            (transaction_matches, case((transaction_remaining > 0, transaction_remaining), else_=0)),
            (base_matches, case((base_remaining > 0, base_remaining), else_=0)),
            else_=0,
        ),
        or_(transaction_matches, base_matches),
    )
