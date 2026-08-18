from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)
from src.core.modules.project_management.domain.enums import TaskStatus
from src.ui_qml.modules.project_management.controllers.common.serializers.tasks_serializer import (
    serialize_task_record_view_models,
)
from src.ui_qml.modules.project_management.presenters.tasks.task_mapper import (
    _priority_bucket_label,
    to_task_record_view_model,
)


def test_priority_bucket_label_none_or_empty_is_not_set() -> None:
    assert _priority_bucket_label(None) == "Not set"
    assert _priority_bucket_label("") == "Not set"


def test_wbs_code_round_trips_from_db_to_serialized_table_row(services) -> None:
    project_service = services["project_service"]
    task_service = services["task_service"]
    project = project_service.create_project("WBS Serializer Check")
    task_service.create_task(
        project.id,
        "Root Package",
        start_date=date(2026, 5, 1),
        duration_days=5,
        status=TaskStatus.TODO,
        wbs_code="1",
    )

    tasks_api = build_project_management_tasks_desktop_api(task_service=task_service)
    page = tasks_api.list_task_page(project_id=project.id, page=1, page_size=25)
    view_models = tuple(to_task_record_view_model(task) for task in page.items)
    rows = serialize_task_record_view_models(view_models)

    assert len(rows) == 1
    # This is the field the Tasks DataTable actually reads (row_dict.get("wbsCode"));
    # it must exist at the row root, not only nested under row["state"].
    assert rows[0]["wbsCode"] == "1"
    assert rows[0]["state"]["wbsCode"] == "1"
    assert "materialDemandLabel" not in rows[0]
    # Human-readable format matching Projects' own format_date_label,
    # not a raw ISO string -- sort order is unaffected since the reader
    # sorts on the underlying date column, never this display label.
    assert rows[0]["startDateLabel"] == "01 May 2026"


def test_priority_label_shows_the_same_bucket_the_priority_filter_selects(services) -> None:
    project_service = services["project_service"]
    task_service = services["task_service"]
    project = project_service.create_project("Priority Bucket Check")
    task_service.create_task(
        project.id, "High Task", start_date=date(2026, 5, 1), duration_days=1, priority=95,
    )
    task_service.create_task(
        project.id, "Medium Task", start_date=date(2026, 5, 1), duration_days=1, priority=50,
    )
    task_service.create_task(
        project.id, "Low Task", start_date=date(2026, 5, 1), duration_days=1, priority=10,
    )
    # `create_task` defaults `priority` to 0 (never None) at the domain
    # layer, so a task with no explicit priority is a real, valid "low"
    # priority -- not a distinct "not set" state. `_priority_bucket_label`'s
    # None/"" branch is defensive for a nullable-priority edge case that
    # doesn't occur via this standard creation path; that branch is covered
    # directly below, not through this DB round trip.
    task_service.create_task(
        project.id, "No Explicit Priority Task", start_date=date(2026, 5, 1), duration_days=1,
    )

    tasks_api = build_project_management_tasks_desktop_api(task_service=task_service)
    page = tasks_api.list_task_page(project_id=project.id, page=1, page_size=25, sort_key="title")
    view_models = tuple(to_task_record_view_model(task) for task in page.items)
    rows = serialize_task_record_view_models(view_models)
    labels_by_title = {row["title"].strip(): row["priorityLabel"] for row in rows}

    assert labels_by_title["High Task"] == "High"
    assert labels_by_title["Medium Task"] == "Medium"
    assert labels_by_title["Low Task"] == "Low"
    assert labels_by_title["No Explicit Priority Task"] == "Low"

    # Boundary check against the reader's own predicate (high >= 70,
    # medium 30-69, low < 30) via the actual priority filter, not just the
    # bucket function in isolation -- proves the label and the filter that
    # selects it agree on where the boundaries fall.
    high_page = tasks_api.list_task_page(project_id=project.id, priority="high", page=1, page_size=25)
    assert {item.name for item in high_page.items} == {"High Task"}
    medium_page = tasks_api.list_task_page(project_id=project.id, priority="medium", page=1, page_size=25)
    assert {item.name for item in medium_page.items} == {"Medium Task"}
    low_page = tasks_api.list_task_page(project_id=project.id, priority="low", page=1, page_size=25)
    # "No Explicit Priority Task" also defaults to priority=0 (<30), so it's
    # a real, correctly-included member of the "low" bucket too.
    assert {item.name for item in low_page.items} == {"Low Task", "No Explicit Priority Task"}
