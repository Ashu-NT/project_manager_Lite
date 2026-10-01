from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    MetaData,
    String,
    Table,
    create_engine,
    select,
)

from src.core.global_overview.application.ordering import sort_action_center_items
from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
    ActionCenterCursor,
    ActionCenterItemDto,
)
from src.core.global_overview.infrastructure.persistence.reads.action_center import (
    action_window,
)


def test_sql_seek_matches_canonical_order_for_dates_nulls_minimum_and_microseconds():
    table = Table("actions", MetaData(), Column("id", String, primary_key=True),
                  Column("due", Date), Column("recency", DateTime))
    engine = create_engine("sqlite://")
    table.metadata.create_all(engine)
    rows = [
        {"id": "a", "due": None, "recency": None},
        {"id": "b", "due": None, "recency": datetime.min},
        {"id": "c", "due": None, "recency": datetime(2026, 1, 1, microsecond=1)},
        {"id": "d", "due": None, "recency": datetime(2026, 1, 1, microsecond=2)},
        {"id": "e", "due": date(2026, 1, 1), "recency": None},
        {"id": "f", "due": date(2026, 1, 1), "recency": datetime(2026, 1, 2)},
        {"id": "g", "due": date(2025, 12, 31), "recency": None},
        {"id": "h", "due": date.max, "recency": None},
    ]
    facts = [ActionCenterItemDto(id=row["id"], kind="task", title="Task", module="PM",
        subject_type="task", subject_id=row["id"], subject_display="Task", action_state="open",
        route_id="workspace", due_at=row["due"], sort_at=row["recency"]) for row in rows]
    expected = [item.id for item in sort_action_center_items(facts, today=date(2026, 1, 1))]
    context = ActionCenterContext("u", "t", "o")
    after = None
    seen = []
    with engine.begin() as connection:
        connection.execute(table.insert(), rows)
        while True:
            page = connection.execute(action_window(select(table), due=table.c.due,
                recency=table.c.recency, module="PM", kind="task", identity=table.c.id,
                after=after, limit=2)).all()
            if not page:
                break
            seen.extend(row.id for row in page)
            last = page[-1]
            after = ActionCenterCursor(context, last.due, last.recency, "PM", "task", last.id)
    engine.dispose()
    assert seen == expected
