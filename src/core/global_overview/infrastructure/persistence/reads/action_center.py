"""SQL counterpart of the generic Action Center ordering, without module tables."""

from datetime import date, datetime

from sqlalchemy import and_, case, func, literal, or_


def action_window(statement, *, due, recency, module, kind, identity, after, limit):
    # Overdue/today/future are already ordered by ascending actual due date.
    # No-date actions follow, in descending authoritative timestamp order.
    missing_due = case((due.is_(None), 1), else_=0)
    due_value = func.coalesce(due, date.max)
    missing_recency = case((due.is_(None) & recency.is_(None), 1), else_=0)
    recent_value = case((due.is_not(None), datetime.min), else_=func.coalesce(recency, datetime.min))
    columns = (missing_due, due_value, missing_recency, recent_value, literal(module), literal(kind), identity)
    directions = (1, 1, 1, -1, 1, 1, 1)
    if after is not None:
        values = (int(after.due_at is None), after.due_at or date.max,
                  int(after.due_at is None and after.sort_at is None),
                  datetime.min if after.due_at else (after.sort_at or datetime.min),
                  after.module, after.kind, after.id)
        predicates = []
        for index, (column, value, direction) in enumerate(zip(columns, values, directions)):
            predicates.append(and_(*(columns[n] == values[n] for n in range(index)),
                                   column > value if direction == 1 else column < value))
        statement = statement.where(or_(*predicates))
    return statement.order_by(*(column.asc() if direction == 1 else column.desc()
                                for column, direction in zip(columns, directions))).limit(min(101, max(0, limit)))
