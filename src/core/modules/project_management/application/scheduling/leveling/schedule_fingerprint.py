"""R4.4L -- staleness/concurrency token for a leveling preview.

A ``LevelingProposal`` is computed against an in-memory snapshot of
tasks/dependencies/assignments. By the time a user chooses to Apply it,
that snapshot may no longer match the database (another edit, another
leveling run, a dependency change). Rather than diffing full field
content or sending per-task version numbers to QML, this module reduces
the entire snapshot to one opaque, deterministic token: a hash of every
involved row's ``(id, version)`` pair. Apply (R4.4M) recomputes this
same token from the current database state immediately before
persisting and rejects the command if it does not match -- the smallest
mechanism that still catches every relevant kind of drift, since ANY
mutation to a Task/TaskDependency/TaskAssignment increments its
`version` field.
"""
from __future__ import annotations

import hashlib

from src.core.modules.project_management.domain.tasks.task import (
    Task,
    TaskAssignment,
    TaskDependency,
)


def compute_schedule_fingerprint(
    tasks_by_id: dict[str, Task],
    deps: list[TaskDependency],
    assignments: list[TaskAssignment],
) -> str:
    """Deterministic token for exactly this set of rows at exactly these
    versions. Same input (in any order) always yields the same token;
    any version bump on any involved row yields a different one."""
    parts: list[str] = []
    for task_id in sorted(tasks_by_id):
        parts.append(f"t:{task_id}:{tasks_by_id[task_id].version}")
    for dep in sorted(deps, key=lambda d: d.id):
        parts.append(f"d:{dep.id}:{dep.version}")
    for assignment in sorted(assignments, key=lambda a: a.id):
        parts.append(f"a:{assignment.id}:{assignment.version}")
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest


__all__ = ["compute_schedule_fingerprint"]
