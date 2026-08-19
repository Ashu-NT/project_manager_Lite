"""Phase N/N5: the Dependencies table must never display a raw task UUID,
and the row-selection state must carry the related task's own dates so the
Task Detail inspector (N6) can render "Related task dates" without QML
computing or re-fetching anything itself.
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.tasks.dependencies_builder import (
    build_dependencies_collection,
)
from src.ui_qml.modules.project_management.presenters.tasks.dependency_mapper import (
    to_dependency_record_view_model,
)


def _fake_dependency(**overrides):
    defaults = dict(
        id="dep-1",
        direction="PREDECESSOR",
        direction_label="Predecessor",
        linked_task_id="task-2",
        linked_task_name="Foundation Complete",
        dependency_type="FS",
        dependency_type_label="Finish -> Start",
        lag_days=2,
        relationship_label="Foundation Complete -> Current Task",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_mapper_never_exposes_the_linked_task_uuid_as_display_text():
    view_model = to_dependency_record_view_model(_fake_dependency())

    assert "task-2" not in view_model.meta_text
    assert "task-2" not in view_model.subtitle
    assert "task-2" not in view_model.supporting_text
    assert view_model.meta_text == "+2d"


def test_mapper_carries_linked_task_dates_when_linked_task_is_known():
    linked_task = SimpleNamespace(
        id="task-2",
        start_date=date(2026, 9, 9),
        end_date=date(2026, 9, 11),
    )

    view_model = to_dependency_record_view_model(_fake_dependency(), linked_task=linked_task)

    assert view_model.state["linkedTaskStartLabel"] == "2026-09-09"
    assert view_model.state["linkedTaskFinishLabel"] == "2026-09-11"


def test_mapper_degrades_to_placeholder_when_linked_task_is_unresolved():
    """The linked task can be missing (deleted/out of scope) -- must show
    an explicit placeholder, never crash or fabricate a date."""
    view_model = to_dependency_record_view_model(_fake_dependency(), linked_task=None)

    assert view_model.state["linkedTaskStartLabel"] == "--"
    assert view_model.state["linkedTaskFinishLabel"] == "--"


def test_build_dependencies_collection_resolves_linked_task_dates_from_all_tasks():
    selected_task = SimpleNamespace(id="task-1")
    linked_task = SimpleNamespace(id="task-2", start_date=date(2026, 9, 9), end_date=date(2026, 9, 11))

    collection = build_dependencies_collection(
        selected_task=selected_task,
        all_tasks=(selected_task, linked_task),
        dependencies=(_fake_dependency(),),
    )

    assert len(collection.items) == 1
    assert collection.items[0].state["linkedTaskStartLabel"] == "2026-09-09"
    assert collection.items[0].state["linkedTaskFinishLabel"] == "2026-09-11"
