from datetime import date

import pytest

from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError


def _create_entry_context(services):
    projects = services["project_service"]
    tasks = services["task_service"]
    resources = services["resource_service"]

    project = projects.create_project("R5H TimeEntry Project")
    task = tasks.create_task(
        project.id,
        "R5H TimeEntry Task",
        start_date=date(2026, 8, 24),
        duration_days=3,
    )
    resource = resources.create_resource("R5H TimeEntry Resource")
    assignment = tasks.assign_resource(task.id, resource.id, allocation_percent=100.0)
    entry = tasks.add_time_entry(
        assignment.id,
        entry_date=date(2026, 8, 24),
        hours=4.0,
        note="Initial work",
    )
    return tasks, services["timesheet_service"], assignment, entry


def test_time_entry_update_and_delete_reject_stale_versions(services) -> None:
    tasks, timesheets, _, entry = _create_entry_context(services)

    updated = tasks.update_time_entry(
        entry.id,
        expected_version=entry.version,
        hours=5.0,
        note="Updated work",
    )
    assert updated.version == 2

    with pytest.raises(ConcurrencyError):
        tasks.update_time_entry(
            entry.id,
            expected_version=1,
            hours=6.0,
        )
    with pytest.raises(ConcurrencyError):
        tasks.delete_time_entry(entry.id, expected_version=1)

    tasks.delete_time_entry(entry.id, expected_version=updated.version)
    with pytest.raises(NotFoundError, match="not found"):
        timesheets.get_time_entry(entry.id)


def test_time_entry_update_rolls_back_when_required_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tasks, timesheets, assignment, entry = _create_entry_context(services)

    def fail_audit(**_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(services["enterprise_audit_service"], "record", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        tasks.update_time_entry(
            entry.id,
            expected_version=entry.version,
            hours=9.0,
            note="Must roll back",
        )

    persisted = timesheets.get_time_entry(entry.id)
    assert persisted.hours == 4.0
    assert persisted.note == "Initial work"
    assert persisted.version == 1
    assert tasks.get_assignment(assignment.id).hours_logged == pytest.approx(4.0)
