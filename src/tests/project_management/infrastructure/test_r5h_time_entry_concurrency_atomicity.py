from datetime import date

import pytest

from src.core.platform.common.exceptions import ConcurrencyError, NotFoundError


def _create_entry_context(services):
    project = services['project_create'].create_project("R5H TimeEntry Project")
    task = services['task_lifecycle_commands'].create_task(
        project.id,
        "R5H TimeEntry Task",
        start_date=date(2026, 8, 24),
        duration_days=3,
    )
    resource = services["resource_master_commands"].create_resource("R5H TimeEntry Resource")
    assignment = services['task_assignment_commands'].assign_resource(task.id, resource.id, allocation_percent=100.0)
    entry = services["time_entry_commands"].add_time_entry(
        assignment.id,
        entry_date=date(2026, 8, 24),
        hours=4.0,
        note="Initial work",
    )
    return services["time_entry_commands"], assignment, entry


def test_time_entry_update_and_delete_reject_stale_versions(services) -> None:
    timesheets, _, entry = _create_entry_context(services)

    updated = timesheets.update_time_entry(
        entry.id,
        expected_version=entry.version,
        hours=5.0,
        note="Updated work",
    )
    assert updated.version == 2

    with pytest.raises(ConcurrencyError):
        timesheets.update_time_entry(
            entry.id,
            expected_version=1,
            hours=6.0,
        )
    with pytest.raises(ConcurrencyError):
        timesheets.delete_time_entry(entry.id, expected_version=1)

    timesheets.delete_time_entry(entry.id, expected_version=updated.version)
    with pytest.raises(NotFoundError, match="not found"):
        services["time_entry_queries"].get_time_entry(entry.id)


def test_time_entry_update_rolls_back_when_required_audit_fails(
    services,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    timesheets, assignment, entry = _create_entry_context(services)

    def fail_audit(**_kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(services["enterprise_audit_service"], "record", fail_audit)

    with pytest.raises(RuntimeError, match="audit unavailable"):
        timesheets.update_time_entry(
            entry.id,
            expected_version=entry.version,
            hours=9.0,
            note="Must roll back",
        )

    persisted = services["time_entry_queries"].get_time_entry(entry.id)
    assert persisted.hours == 4.0
    assert persisted.note == "Initial work"
    assert persisted.version == 1
    assert services["task_assignment_commands"].get_assignment(
        assignment.id
    ).hours_logged == pytest.approx(4.0)
