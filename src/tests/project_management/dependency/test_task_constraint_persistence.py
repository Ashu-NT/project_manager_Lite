"""Task.constraint_type/constraint_date persistence -- the ORM/mapper/
repository vertical slice (R4.4 constraint audit §4 gap: DB columns
existed from an old migration but were never mapped/round-tripped/
written by the version-checked update). Exercises the real
TaskRepository, not a fake, since that's exactly the layer the gap was
in.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.platform.common.exceptions import ConcurrencyError


def _repo(services):
    return services["task_service"]._task_repo


@pytest.mark.parametrize(
    "constraint_type",
    [
        ConstraintType.MUST_START_ON,
        ConstraintType.MUST_FINISH_ON,
        ConstraintType.START_NO_EARLIER_THAN,
        ConstraintType.START_NO_LATER_THAN,
        ConstraintType.FINISH_NO_EARLIER_THAN,
        ConstraintType.FINISH_NO_LATER_THAN,
    ],
)
def test_every_editable_constraint_type_round_trips_through_persistence(services, constraint_type):
    ps = services["project_service"]
    ts = services["task_service"]
    repo = _repo(services)
    project = ps.create_project("Constraint Persistence", "")
    task = ts.create_task(project.id, "Constrained Task", "", start_date=date(2026, 9, 1), duration_days=3)

    from dataclasses import replace

    constrained = replace(
        task, constraint_type=constraint_type, constraint_date=date(2026, 9, 18)
    )
    repo.update(constrained)

    reloaded = repo.get(task.id)
    assert reloaded.constraint_type is constraint_type
    assert reloaded.constraint_date == date(2026, 9, 18)


def test_no_constraint_round_trips_as_none(services):
    ps = services["project_service"]
    ts = services["task_service"]
    repo = _repo(services)
    project = ps.create_project("Constraint Persistence No Constraint", "")
    task = ts.create_task(project.id, "Plain Task", "", start_date=date(2026, 9, 1), duration_days=3)

    reloaded = repo.get(task.id)
    assert reloaded.constraint_type is None
    assert reloaded.constraint_date is None


def test_clearing_a_constraint_round_trips_as_none(services):
    ps = services["project_service"]
    ts = services["task_service"]
    repo = _repo(services)
    project = ps.create_project("Constraint Persistence Clear", "")
    task = ts.create_task(project.id, "Constrained Task", "", start_date=date(2026, 9, 1), duration_days=3)

    from dataclasses import replace

    constrained = replace(
        task,
        constraint_type=ConstraintType.START_NO_EARLIER_THAN,
        constraint_date=date(2026, 9, 18),
    )
    repo.update(constrained)
    assert repo.get(task.id).constraint_type is ConstraintType.START_NO_EARLIER_THAN

    cleared = replace(repo.get(task.id), constraint_type=None, constraint_date=None)
    repo.update(cleared)

    reloaded = repo.get(task.id)
    assert reloaded.constraint_type is None
    assert reloaded.constraint_date is None


def test_is_milestone_update_persists(services):
    """Regression: is_milestone was absent from TaskRepository.update's
    version-checked write-column dict -- a change to it via update_task
    silently never persisted. Fixed alongside the constraint columns
    while touching this exact dict."""
    ps = services["project_service"]
    ts = services["task_service"]
    repo = _repo(services)
    project = ps.create_project("Milestone Persistence Update", "")
    task = ts.create_task(project.id, "Regular Task", "", start_date=date(2026, 9, 1), duration_days=3)
    assert repo.get(task.id).is_milestone is False

    from dataclasses import replace

    made_milestone = replace(task, is_milestone=True, duration_days=0)
    repo.update(made_milestone)

    reloaded = repo.get(task.id)
    assert reloaded.is_milestone is True


def test_constraint_update_respects_optimistic_concurrency(services):
    ps = services["project_service"]
    ts = services["task_service"]
    repo = _repo(services)
    project = ps.create_project("Constraint Persistence Concurrency", "")
    task = ts.create_task(project.id, "Constrained Task", "", start_date=date(2026, 9, 1), duration_days=3)

    from dataclasses import replace

    stale = replace(
        task,
        constraint_type=ConstraintType.MUST_START_ON,
        constraint_date=date(2026, 9, 18),
        version=task.version + 1,
    )
    with pytest.raises(ConcurrencyError):
        repo.update(stale)

    # The real (non-stale) version must still succeed afterward.
    fresh = replace(
        repo.get(task.id),
        constraint_type=ConstraintType.MUST_START_ON,
        constraint_date=date(2026, 9, 18),
    )
    repo.update(fresh)
    assert repo.get(task.id).constraint_type is ConstraintType.MUST_START_ON
