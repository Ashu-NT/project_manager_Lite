from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.scheduling.schedule_sort import (
    normalize_schedule_sort,
    sort_schedule_items,
)


def _item(item_id: str, name: str, start_date: date | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=item_id,
        name=name,
        wbs_code=item_id,
        start_date=start_date,
        finish_date=start_date,
        duration_days=1,
        remaining_duration_days=1,
        total_float_days=0,
        is_critical=False,
        actual_start=None,
        actual_end=None,
        deadline=None,
        percent_complete=0.0,
        status_label="To Do",
    )


def test_schedule_sort_orders_complete_collection_before_page_slicing() -> None:
    items = tuple(
        _item(str(index), f"Activity {index:02d}", date(2026, 8, index))
        for index in range(1, 13)
    )
    ascending_sort = normalize_schedule_sort(key="taskName", direction="asc")
    descending_sort = normalize_schedule_sort(key="taskName", direction="desc")

    ascending = sort_schedule_items(items, sort=ascending_sort)
    descending = sort_schedule_items(items, sort=descending_sort)

    assert [item.name for item in ascending[:10]][:2] == ["Activity 01", "Activity 02"]
    assert [item.name for item in ascending[10:]] == ["Activity 11", "Activity 12"]
    assert [item.name for item in descending[:10]][:2] == ["Activity 12", "Activity 11"]
    assert [item.name for item in descending[10:]] == ["Activity 02", "Activity 01"]


def test_schedule_sort_is_allowlisted_and_keeps_missing_dates_last() -> None:
    items = (
        _item("missing", "Missing", None),
        _item("later", "Later", date(2026, 8, 2)),
        _item("earlier", "Earlier", date(2026, 8, 1)),
    )

    descending = sort_schedule_items(
        items,
        sort=normalize_schedule_sort(key="start", direction="desc"),
    )
    unsupported = normalize_schedule_sort(key="arbitrary_code", direction="desc")

    assert [item.id for item in descending] == ["later", "earlier", "missing"]
    assert unsupported.key == "schedule"
    assert unsupported.direction.value == "asc"
    assert sort_schedule_items(items, sort=unsupported) == items
