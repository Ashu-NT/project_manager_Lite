"""Typed, non-persisting impact preview for dependency changes: create/update via
``get_dependency_diagnostics(..., include_impact=True)``, delete via
``preview_dependency_removal``. Both use the exact same canonical ``run_cpm`` path the committed
schedule uses, so a preview can never disagree with what saving/removing would actually produce.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.application.projects.dto.commands.project_lifecycle import (
    ProjectCreateCommand,
)
from src.core.modules.project_management.domain.enums import DependencyType


def _make_chain(services):
    """A -> B -> C, all FS lag 0."""
    project = services['project_create'].create_project(ProjectCreateCommand(name="Impact Preview", description=""))
    a = services['task_lifecycle_commands'].create_task(project.id, "Task A", "", start_date=date(2023, 11, 6), duration_days=2)
    b = services['task_lifecycle_commands'].create_task(project.id, "Task B", "", duration_days=2)
    c = services['task_lifecycle_commands'].create_task(project.id, "Task C", "", duration_days=2)
    dep_ab = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    services['task_dependency_commands'].add_dependency(b.id, c.id, DependencyType.FINISH_TO_START, lag_days=0)
    return project, a, b, c, dep_ab


def test_removal_preview_reports_no_shift_when_successor_has_no_other_anchor(services):
    """Not a bug: CPM persists A->B's computed date onto B.start_date on commit, so if B loses
    that dependency, the "without" simulation falls back to B's own already-persisted
    start_date -- reproducing the same date and correctly reporting no shift. Removing a task's
    only incoming dependency does not retroactively un-schedule it."""
    _project, a, b, c, dep_ab = _make_chain(services)

    preview = services["task_dependency_diagnostics"].preview_dependency_removal(dep_ab.id)

    assert preview.is_valid is True
    assert preview.code == "DEPENDENCY_VALID"
    assert preview.predecessor_task_id == a.id
    assert preview.successor_task_id == b.id
    assert preview.impact_rows == []
    assert preview.risk_level == "none"


def test_removal_preview_reports_shift_when_successor_has_its_own_conflicting_start_date(services):
    """Once B has its OWN explicit start_date (set independent of the
    dependency, before the dependency existed or edited directly), the FS
    dependency overrides it entirely while the edge exists (dependencies
    ignore a task's own start_date whenever incoming_deps is non-empty).
    Removing the edge reveals that underlying, previously-overridden
    start_date -- a real, reportable shift."""
    project = services['project_create'].create_project(ProjectCreateCommand(name="Impact Preview Isolated", description=""))
    a = services['task_lifecycle_commands'].create_task(project.id, "Task A", "", start_date=date(2023, 11, 6), duration_days=2)
    b = services['task_lifecycle_commands'].create_task(project.id, "Task B", "", start_date=date(2024, 1, 1), duration_days=1)
    dep = services['task_dependency_commands'].add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    preview = services["task_dependency_diagnostics"].preview_dependency_removal(dep.id)

    affected_ids = {row.task_id for row in preview.impact_rows}
    assert b.id in affected_ids
    assert preview.risk_level != "none"


def test_removal_preview_reports_not_found_for_unknown_id(services):
    preview = services["task_dependency_diagnostics"].preview_dependency_removal("does-not-exist")
    assert preview.is_valid is False
    assert preview.code == "DEPENDENCY_NOT_FOUND"


def test_removal_preview_never_mutates_anything(services):
    """The preview is advisory -- it must not persist the removal or touch
    the schedule."""
    _project, a, b, c, dep_ab = _make_chain(services)

    services["task_dependency_diagnostics"].preview_dependency_removal(dep_ab.id)

    assert services['task_dependency_query'].get_dependency(dep_ab.id) is not None
    deps = services['task_dependency_query'].list_dependencies_for_task(b.id)
    assert any(d.id == dep_ab.id for d in deps)
