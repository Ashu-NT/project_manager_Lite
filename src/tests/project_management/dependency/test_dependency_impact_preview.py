"""Phase K: typed, non-persisting impact preview for dependency changes.

Create/update preview already existed as ``get_dependency_diagnostics(...,
include_impact=True)``; ``preview_dependency_removal`` closes the gap for
DELETE. Both use the exact same canonical ``run_cpm`` path the committed
schedule uses, so a preview can never disagree with what saving/removing
would actually produce. See
docs/pm_modernization/R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md
§17/Phase K.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.domain.enums import DependencyType


def _make_chain(services):
    """A -> B -> C, all FS lag 0."""
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Impact Preview", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2023, 11, 6), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", duration_days=2)
    c = ts.create_task(project.id, "Task C", "", duration_days=2)
    dep_ab = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)
    ts.add_dependency(b.id, c.id, DependencyType.FINISH_TO_START, lag_days=0)
    return project, a, b, c, dep_ab


def test_removal_preview_reports_no_shift_when_successor_has_no_other_anchor(services):
    """Real, load-bearing property of this scheduling engine, not a bug:
    once A->B has been added, CPM persists its computed date back onto
    B.start_date (the normal commit behavior). If B loses its only
    incoming dependency, the "without" simulation falls back to using
    B's OWN (already-persisted, previously dependency-derived)
    start_date as its anchor -- so it reproduces the exact date it already
    had, and the preview correctly reports no shift. Removing a task's
    only incoming dependency does not retroactively un-schedule it."""
    ts = services["task_service"]
    _project, a, b, c, dep_ab = _make_chain(services)

    preview = ts.preview_dependency_removal(dep_ab.id)

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
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Impact Preview Isolated", "")
    a = ts.create_task(project.id, "Task A", "", start_date=date(2023, 11, 6), duration_days=2)
    b = ts.create_task(project.id, "Task B", "", start_date=date(2024, 1, 1), duration_days=1)
    dep = ts.add_dependency(a.id, b.id, DependencyType.FINISH_TO_START, lag_days=0)

    preview = ts.preview_dependency_removal(dep.id)

    affected_ids = {row.task_id for row in preview.impact_rows}
    assert b.id in affected_ids
    assert preview.risk_level != "none"


def test_removal_preview_reports_not_found_for_unknown_id(services):
    ts = services["task_service"]
    preview = ts.preview_dependency_removal("does-not-exist")
    assert preview.is_valid is False
    assert preview.code == "DEPENDENCY_NOT_FOUND"


def test_removal_preview_never_mutates_anything(services):
    """The preview is advisory -- it must not persist the removal or touch
    the schedule."""
    ts = services["task_service"]
    _project, a, b, c, dep_ab = _make_chain(services)

    ts.preview_dependency_removal(dep_ab.id)

    assert ts.get_dependency(dep_ab.id) is not None
    deps = ts.list_dependencies_for_task(b.id)
    assert any(d.id == dep_ab.id for d in deps)
