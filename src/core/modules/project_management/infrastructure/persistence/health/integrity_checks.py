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
from src.core.modules.project_management.infrastructure.persistence.orm.cost_calendar import (
    CostItemORM,
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


def run_pm_data_integrity_checks(session: Session, *, sample_limit: int = 20) -> IntegrityReport:
    """Run every PM integrity check and return a structured report.

    Read-only. Safe to run against production data.
    """
    pred = aliased(TaskORM)
    succ = aliased(TaskORM)

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
        # 8. Cost linked to a task that belongs to a different project.
        _finding(
            session,
            category="cost_task_cross_project",
            severity=ERROR,
            message="cost item linked to a task from a different project",
            id_stmt=(
                select(CostItemORM.id)
                .join(TaskORM, CostItemORM.task_id == TaskORM.id)
                .where(CostItemORM.task_id.is_not(None))
                .where(CostItemORM.project_id != TaskORM.project_id)
            ),
            sample_limit=sample_limit,
        ),
        # 9. Orphan cost — cost pointing at a non-existent project.
        _finding(
            session,
            category="orphan_cost",
            severity=ERROR,
            message="cost item references a project that does not exist",
            id_stmt=select(CostItemORM.id).where(
                CostItemORM.project_id.notin_(select(ProjectORM.id))
            ),
            sample_limit=sample_limit,
        ),
        # 10. Baseline task snapshot whose live task is in a different project.
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
        # 11. Duplicate project-resource link (defense-in-depth; a unique index exists).
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
        # 12. Resource over-allocation (heuristic, date-agnostic sum of allocation %).
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
    ]
    return IntegrityReport(tuple(checks))


__all__ = ["IntegrityFinding", "IntegrityReport", "run_pm_data_integrity_checks"]
