"""Read-only Project Management data-integrity health checks.

This module inspects PM rows for cross-project contamination and orphaned
records that the application layer is expected to prevent on new writes, but
which may exist in legacy data created before those guards (or before the
recommended unique constraints) were in place.

It is strictly READ-ONLY — it issues SELECT statements only and never mutates
data. It is the discovery step that MUST run (and any findings be cleaned)
before the project-scope unique constraints are added by migration.

Usage (CLI):  python -m tools.pm_data_integrity_check
Usage (code): report = run_pm_data_integrity_checks(session)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import and_, exists, func, select
from sqlalchemy.orm import Session, aliased

from src.core.modules.project_management.infrastructure.persistence.orm.baseline import (
    BaselineTaskORM,
    ProjectBaselineORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.project import (
    ProjectORM,
    ProjectResourceORM,
)
from src.core.modules.project_management.infrastructure.persistence.orm.task import (
    TaskAssignmentORM,
    TaskDependencyORM,
    TaskORM,
)

# Severity levels (ordered by gravity).
ERROR = "error"      # data that breaks a hard project-scope invariant
WARNING = "warning"  # data that violates a uniqueness/business rule
REVIEW = "review"    # heuristic flag that needs human judgement


@dataclass(frozen=True)
class IntegrityFinding:
    """A single check result. ``count == 0`` means the check passed."""

    category: str
    severity: str
    message: str
    count: int = 0
    sample_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.count == 0


@dataclass(frozen=True)
class IntegrityReport:
    findings: tuple[IntegrityFinding, ...]

    @property
    def ok(self) -> bool:
        return all(f.ok for f in self.findings)

    @property
    def problems(self) -> tuple[IntegrityFinding, ...]:
        return tuple(f for f in self.findings if not f.ok)

    def to_lines(self) -> list[str]:
        lines = ["Project Management — Data Integrity Report", "=" * 44]
        if self.ok:
            lines.append("OK — no integrity problems detected.")
            return lines
        for finding in self.problems:
            sample = ", ".join(finding.sample_ids)
            lines.append(
                f"[{finding.severity.upper():7}] {finding.category}: "
                f"{finding.count} row(s) — {finding.message}"
            )
            if sample:
                lines.append(f"            sample: {sample}")
        lines.append("")
        lines.append(f"{len(self.problems)} check(s) flagged problems.")
        return lines


def _finding(
    session: Session,
    *,
    category: str,
    severity: str,
    message: str,
    id_stmt,
    sample_limit: int,
) -> IntegrityFinding:
    """Run ``id_stmt`` (a SELECT of identifier rows) and build a finding."""
    rows = session.execute(id_stmt).all()
    sample = tuple(str(_row_to_id(row)) for row in rows[:sample_limit])
    return IntegrityFinding(
        category=category,
        severity=severity,
        message=message,
        count=len(rows),
        sample_ids=sample,
    )


def _row_to_id(row) -> str:
    if len(row) == 1:
        return row[0]
    return ":".join("" if value is None else str(value) for value in row)


def _wbs_cycle_finding(session: Session, *, sample_limit: int) -> IntegrityFinding:
    parents = {
        str(task_id): (str(parent_id) if parent_id is not None else None)
        for task_id, parent_id in session.execute(
            select(TaskORM.id, TaskORM.parent_task_id)
        ).all()
    }
    cycle_ids: set[str] = set()
    for start_id in parents:
        path: list[str] = []
        positions: dict[str, int] = {}
        current: str | None = start_id
        while current is not None and current in parents:
            if current in positions:
                cycle_ids.update(path[positions[current] :])
                break
            positions[current] = len(path)
            path.append(current)
            current = parents[current]
    ordered = tuple(sorted(cycle_ids))
    return IntegrityFinding(
        category="task_wbs_cycle",
        severity=ERROR,
        message="task WBS parent chain contains a cycle",
        count=len(ordered),
        sample_ids=ordered[:sample_limit],
    )


def _dependency_cycle_finding(session: Session, *, sample_limit: int) -> IntegrityFinding:
    """Detect a persisted Task->Task dependency cycle -- i.e. a graph that
    should never have been writable (creation-time cycle detection has
    covered this since before this check existed), but the approval-apply
    TOCTOU hole fixed in
    docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
    §10/Phase I meant one COULD have been persisted by two
    concurrently-approved requests each individually valid at request time.
    Before this check existed, a persisted cycle was invisible to
    `python -m tools.pm_data_integrity_check` and would only surface later
    as a `SCHEDULE_CYCLE` crash the next time CPM ran for that project.

    Uses the same DFS three-color cycle detection idiom as
    ``_wbs_cycle_finding`` above, generalized from a single-parent tree
    walk to a general graph (a task can have multiple predecessors and
    successors, unlike the WBS parent chain)."""
    edges = session.execute(
        select(
            TaskDependencyORM.id,
            TaskDependencyORM.predecessor_task_id,
            TaskDependencyORM.successor_task_id,
        )
    ).all()

    adjacency: dict[str, list[str]] = {}
    edge_id_by_pair: dict[tuple[str, str], str] = {}
    for dep_id, predecessor_id, successor_id in edges:
        adjacency.setdefault(str(predecessor_id), []).append(str(successor_id))
        edge_id_by_pair[(str(predecessor_id), str(successor_id))] = str(dep_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {task_id: WHITE for task_id in adjacency}
    for successors in adjacency.values():
        for succ in successors:
            color.setdefault(succ, WHITE)

    cycle_edge_ids: set[str] = set()

    def _visit(node: str, stack: list[str]) -> None:
        color[node] = GRAY
        stack.append(node)
        for successor in adjacency.get(node, []):
            if color.get(successor, WHITE) == WHITE:
                _visit(successor, stack)
            elif color.get(successor) == GRAY:
                # Back-edge to an ancestor still on the stack: walk the
                # stack from that ancestor to here to collect every edge
                # id on the cycle.
                start = stack.index(successor)
                cycle_nodes = stack[start:] + [successor]
                for a, b in zip(cycle_nodes, cycle_nodes[1:]):
                    edge_id = edge_id_by_pair.get((a, b))
                    if edge_id is not None:
                        cycle_edge_ids.add(edge_id)
        stack.pop()
        color[node] = BLACK

    for task_id in list(adjacency):
        if color.get(task_id, WHITE) == WHITE:
            _visit(task_id, [])

    ordered = tuple(sorted(cycle_edge_ids))
    return IntegrityFinding(
        category="dependency_cycle",
        severity=ERROR,
        message="task dependency graph contains a cycle",
        count=len(ordered),
        sample_ids=ordered[:sample_limit],
    )


def run_pm_data_integrity_checks(session: Session, *, sample_limit: int = 20) -> IntegrityReport:
    """Run every PM integrity check and return a structured report.

    Read-only. Safe to run against production data.
    """
    pred = aliased(TaskORM)
    succ = aliased(TaskORM)
    wbs_parent = aliased(TaskORM)

    checks = [
        # 1. Orphan tasks — task pointing at a non-existent project.
        _finding(
            session,
            category="orphan_task",
            severity=ERROR,
            message="task references a project that does not exist",
            id_stmt=select(TaskORM.id).where(
                TaskORM.project_id.notin_(select(ProjectORM.id))
            ),
            sample_limit=sample_limit,
        ),
        _finding(
            session,
            category="task_wbs_cross_project_parent",
            severity=ERROR,
            message="task WBS parent belongs to another project",
            id_stmt=(
                select(TaskORM.id)
                .join(wbs_parent, TaskORM.parent_task_id == wbs_parent.id)
                .where(TaskORM.project_id != wbs_parent.project_id)
            ),
            sample_limit=sample_limit,
        ),
        _finding(
            session,
            category="task_wbs_duplicate_code",
            severity=ERROR,
            message="project contains duplicate WBS codes",
            id_stmt=(
                select(TaskORM.project_id, TaskORM.wbs_code)
                .group_by(TaskORM.project_id, TaskORM.wbs_code)
                .having(func.count() > 1)
            ),
            sample_limit=sample_limit,
        ),
        # 2. Cross-project dependency — predecessor/successor in different projects.
        _finding(
            session,
            category="cross_project_dependency",
            severity=ERROR,
            message="dependency links tasks from two different projects",
            id_stmt=(
                select(TaskDependencyORM.id)
                .join(pred, TaskDependencyORM.predecessor_task_id == pred.id)
                .join(succ, TaskDependencyORM.successor_task_id == succ.id)
                .where(pred.project_id != succ.project_id)
            ),
            sample_limit=sample_limit,
        ),
        # 3. Self dependency — task depends on itself.
        _finding(
            session,
            category="self_dependency",
            severity=ERROR,
            message="dependency links a task to itself",
            id_stmt=select(TaskDependencyORM.id).where(
                TaskDependencyORM.predecessor_task_id == TaskDependencyORM.successor_task_id
            ),
            sample_limit=sample_limit,
        ),
        # 4. Duplicate dependency pair.
        _finding(
            session,
            category="duplicate_dependency",
            severity=WARNING,
            message="duplicate (predecessor, successor) dependency pair",
            id_stmt=(
                select(
                    TaskDependencyORM.predecessor_task_id,
                    TaskDependencyORM.successor_task_id,
                )
                .group_by(
                    TaskDependencyORM.predecessor_task_id,
                    TaskDependencyORM.successor_task_id,
                )
                .having(func.count() > 1)
            ),
            sample_limit=sample_limit,
        ),
        # 4b. Task dependency cycle (see _dependency_cycle_finding docstring).
        _dependency_cycle_finding(session, sample_limit=sample_limit),
        # 5. Assignment whose resource is not part of the task's project.
        _finding(
            session,
            category="assignment_resource_not_in_project",
            severity=ERROR,
            message="task assignment for a resource not assigned to the task's project",
            id_stmt=(
                select(TaskAssignmentORM.id)
                .join(TaskORM, TaskAssignmentORM.task_id == TaskORM.id)
                .where(
                    ~exists().where(
                        and_(
                            ProjectResourceORM.project_id == TaskORM.project_id,
                            ProjectResourceORM.resource_id == TaskAssignmentORM.resource_id,
                        )
                    )
                )
            ),
            sample_limit=sample_limit,
        ),
        # 6. Assignment's project_resource belongs to a different project than its task.
        _finding(
            session,
            category="assignment_project_resource_mismatch",
            severity=ERROR,
            message="assignment.project_resource_id belongs to a different project than the task",
            id_stmt=(
                select(TaskAssignmentORM.id)
                .join(TaskORM, TaskAssignmentORM.task_id == TaskORM.id)
                .join(
                    ProjectResourceORM,
                    TaskAssignmentORM.project_resource_id == ProjectResourceORM.id,
                )
                .where(ProjectResourceORM.project_id != TaskORM.project_id)
            ),
            sample_limit=sample_limit,
        ),
        # 7. Duplicate (task, resource) assignment.
        _finding(
            session,
            category="duplicate_assignment",
            severity=WARNING,
            message="resource assigned to the same task more than once",
            id_stmt=(
                select(TaskAssignmentORM.task_id, TaskAssignmentORM.resource_id)
                .group_by(TaskAssignmentORM.task_id, TaskAssignmentORM.resource_id)
                .having(func.count() > 1)
            ),
            sample_limit=sample_limit,
        ),
        # 8. Baseline task snapshot whose live task is in a different project.
        _finding(
            session,
            category="baseline_task_cross_project",
            severity=ERROR,
            message="baseline task snapshot references a live task from a different project",
            id_stmt=(
                select(BaselineTaskORM.id)
                .join(ProjectBaselineORM, BaselineTaskORM.baseline_id == ProjectBaselineORM.id)
                .join(TaskORM, BaselineTaskORM.task_id == TaskORM.id)
                .where(TaskORM.project_id != ProjectBaselineORM.project_id)
            ),
            sample_limit=sample_limit,
        ),
        # 9. Duplicate project-resource link (defense-in-depth; a unique index exists).
        _finding(
            session,
            category="duplicate_project_resource",
            severity=WARNING,
            message="resource assigned to the same project more than once",
            id_stmt=(
                select(ProjectResourceORM.project_id, ProjectResourceORM.resource_id)
                .group_by(ProjectResourceORM.project_id, ProjectResourceORM.resource_id)
                .having(func.count() > 1)
            ),
            sample_limit=sample_limit,
        ),
        # 10. Resource over-allocation (heuristic, date-agnostic sum of allocation %).
        _finding(
            session,
            category="resource_overallocation",
            severity=REVIEW,
            message="resource total assignment allocation exceeds 100% (date-agnostic; verify overlap)",
            id_stmt=(
                select(TaskAssignmentORM.resource_id)
                .group_by(TaskAssignmentORM.resource_id)
                .having(func.coalesce(func.sum(TaskAssignmentORM.allocation_percent), 0.0) > 100.0)
            ),
            sample_limit=sample_limit,
        ),
        _wbs_cycle_finding(session, sample_limit=sample_limit),
    ]
    return IntegrityReport(tuple(checks))


__all__ = ["IntegrityFinding", "IntegrityReport", "run_pm_data_integrity_checks"]
