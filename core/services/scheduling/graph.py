from __future__ import annotations

import heapq
from typing import Callable, Dict, List

from core.exceptions import BusinessRuleError
from core.models import Task, TaskDependency


def build_project_dependency_graph(
    tasks_by_id: Dict[str, Task],
    deps: List[TaskDependency],
    priority_value: Callable[[Task], int],
) -> tuple[list[str], dict[str, list[TaskDependency]], dict[str, list[TaskDependency]]]:
    filtered_deps = [
        d
        for d in deps
        if d.predecessor_task_id in tasks_by_id and d.successor_task_id in tasks_by_id
    ]

    graph_succ: Dict[str, List[TaskDependency]] = {}
    indegree: Dict[str, int] = {task_id: 0 for task_id in tasks_by_id}

    for dep in filtered_deps:
        graph_succ.setdefault(dep.predecessor_task_id, []).append(dep)
        indegree[dep.successor_task_id] += 1

    heap: list[tuple[int, str, str]] = []
    for task_id, degree in indegree.items():
        if degree == 0:
            task = tasks_by_id[task_id]
            heapq.heappush(
                heap,
                (priority_value(task), (getattr(task, "name", "") or ""), task_id),
            )

    topo_order: list[str] = []
    while heap:
        _priority, _name, task_id = heapq.heappop(heap)
        topo_order.append(task_id)
        for dep in graph_succ.get(task_id, []):
            succ_id = dep.successor_task_id
            indegree[succ_id] -= 1
            if indegree[succ_id] == 0:
                succ_task = tasks_by_id[succ_id]
                heapq.heappush(
                    heap,
                    (
                        priority_value(succ_task),
                        (getattr(succ_task, "name", "") or ""),
                        succ_id,
                    ),
                )

    if len(topo_order) != len(tasks_by_id):
        raise BusinessRuleError(
            "Cannot schedule project: circular dependency detected.",
            code="SCHEDULE_CYCLE",
        )

    deps_by_successor: Dict[str, List[TaskDependency]] = {}
    deps_by_predecessor: Dict[str, List[TaskDependency]] = {}
    for dep in filtered_deps:
        deps_by_successor.setdefault(dep.successor_task_id, []).append(dep)
        deps_by_predecessor.setdefault(dep.predecessor_task_id, []).append(dep)

    return topo_order, deps_by_successor, deps_by_predecessor

