from core.models import DependencyType, TaskDependency
from ui.task.dependency_dialogs import _dependency_direction


def test_dependency_direction_identifies_predecessor_for_current_successor():
    dep = TaskDependency.create("task_pred", "task_current", DependencyType.FINISH_TO_START, lag_days=2)
    direction, linked_task_id = _dependency_direction("task_current", dep)
    assert direction == "Predecessor"
    assert linked_task_id == "task_pred"


def test_dependency_direction_identifies_successor_for_current_predecessor():
    dep = TaskDependency.create("task_current", "task_succ", DependencyType.START_TO_START, lag_days=0)
    direction, linked_task_id = _dependency_direction("task_current", dep)
    assert direction == "Successor"
    assert linked_task_id == "task_succ"


def test_dependency_direction_returns_none_for_unrelated_dependency():
    dep = TaskDependency.create("task_a", "task_b", DependencyType.FINISH_TO_FINISH, lag_days=1)
    direction, linked_task_id = _dependency_direction("task_other", dep)
    assert direction is None
    assert linked_task_id is None


def test_dependency_add_dialog_shows_risk_and_action_suggestions():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "ui" / "task" / "dependency_add_dialog.py").read_text(
        encoding="utf-8", errors="ignore"
    )
    assert "Risk:" in text
    assert "diag.suggestions[:2]" in text
