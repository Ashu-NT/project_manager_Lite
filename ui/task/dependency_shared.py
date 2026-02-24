from __future__ import annotations

from core.models import TaskDependency

REL_CURRENT_DEPENDS = "current_depends"
REL_OTHER_DEPENDS = "other_depends"


def dependency_direction(task_id: str, dep: TaskDependency) -> tuple[str | None, str | None]:
    if dep.successor_task_id == task_id:
        return "Predecessor", dep.predecessor_task_id
    if dep.predecessor_task_id == task_id:
        return "Successor", dep.successor_task_id
    return None, None


__all__ = ["REL_CURRENT_DEPENDS", "REL_OTHER_DEPENDS", "dependency_direction"]
