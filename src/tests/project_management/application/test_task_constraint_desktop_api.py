"""Phase M (R4.4 constraint pass): desktop API surface for Task
scheduling constraints, exercised against the real services fixture
(not fakes) -- list_constraint_options, create_task with an initial
constraint, and update_task_scheduling_constraint end-to-end.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.tasks.commands.task_commands import (
    TaskConstraintUpdateCommand,
    TaskCreateCommand,
)
from src.core.modules.project_management.api.desktop.tasks.factories.tasks_api_factory import (
    build_project_management_tasks_desktop_api,
)


def test_list_constraint_options_includes_asap_and_six_editable_types(services):
    api = build_project_management_tasks_desktop_api(task_service=services["task_service"])
    options = api.list_constraint_options()

    assert options[0].value == ""
    assert options[0].code == "ASAP"
    codes = {o.code for o in options}
    assert codes == {"ASAP", "SNET", "SNLT", "FNET", "FNLT", "MSO", "MFO"}
    assert all(o.code == "DEADLINE" or o.requires_date or o.code == "ASAP" for o in options)


def test_create_task_with_an_initial_constraint(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Constraint Desktop API Create", "")
    api = build_project_management_tasks_desktop_api(task_service=ts)

    dto = api.create_task(
        TaskCreateCommand(
            project_id=project.id,
            name="Constrained Task",
            start_date=date(2026, 9, 18),
            duration_days=3,
            constraint_type="must_start_on",
            constraint_date=date(2026, 9, 18),
        )
    )

    assert dto.constraint_type == "must_start_on"
    assert dto.constraint_type_label == "Must Start On (MSO)"
    assert dto.constraint_date == date(2026, 9, 18)


def test_update_task_scheduling_constraint_end_to_end(services):
    ps = services["project_service"]
    ts = services["task_service"]
    project = ps.create_project("Constraint Desktop API Update", "")
    api = build_project_management_tasks_desktop_api(task_service=ts)
    created = api.create_task(
        TaskCreateCommand(project_id=project.id, name="Plain Task", start_date=date(2026, 9, 1), duration_days=3)
    )
    assert created.constraint_type == ""

    updated = api.update_task_scheduling_constraint(
        TaskConstraintUpdateCommand(
            task_id=created.id,
            constraint_type="start_no_earlier_than",
            constraint_date=date(2026, 9, 18),
            expected_version=created.version,
        )
    )

    assert updated.constraint_type == "start_no_earlier_than"
    assert updated.constraint_type_label == "Start No Earlier Than (SNET)"
    assert updated.constraint_date == date(2026, 9, 18)

    cleared = api.update_task_scheduling_constraint(
        TaskConstraintUpdateCommand(
            task_id=created.id,
            constraint_type=None,
            constraint_date=None,
            expected_version=updated.version,
        )
    )
    assert cleared.constraint_type == ""
    assert cleared.constraint_date is None
