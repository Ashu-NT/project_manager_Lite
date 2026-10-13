from datetime import date

from src.core.modules.project_management.contracts.ports.schedule_change import (
    ApprovedTaskScheduleChange,
)


def test_approved_schedule_validation_loads_targets_in_batch(services, monkeypatch):
    project = services["project_service"].create_project("Batch schedule approval")
    tasks = services["task_service"]
    first = tasks.create_task(project.id, "First")
    second = tasks.create_task(project.id, "Second")
    changes = [
        ApprovedTaskScheduleChange(
            reference_id=task.id,
            project_id=project.id,
            task_id=task.id,
            expected_version=task.version,
            start_date=date(2026, 8, 17),
            finish_date=date(2026, 8, 18),
        )
        for task in (first, second)
    ]

    def reject_per_target_lookup(*_args, **_kwargs):
        raise AssertionError("approval validation must batch target reads")

    monkeypatch.setattr(tasks._task_repo, "get", reject_per_target_lookup)
    candidates = tasks._validate_approved_schedule_changes(changes)

    assert [task.id for _, task in candidates] == [first.id, second.id]
