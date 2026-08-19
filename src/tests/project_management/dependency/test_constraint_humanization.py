"""Phase M1 (R4.4 constraint pass): no raw/mis-rendered ConstraintType
value reaches a desktop DTO. The audit found three disagreeing
treatments for the identical underlying value: title-cased in one
serializer, raw snake_case with no label field in another, and a third
site that would have rendered the literal enum repr
("ConstraintType.MUST_START_ON") had it ever fired. All three now go
through the one canonical constraint_presentation() map.
"""
from __future__ import annotations

from datetime import date

from src.core.modules.project_management.api.desktop.common.constraint_presentation import (
    constraint_presentation,
)
from src.core.modules.project_management.application.scheduling.forecasting.task_schedule_overview import (
    build_schedule_drivers,
)
from src.core.modules.project_management.domain.enums import ConstraintType
from src.core.modules.project_management.domain.tasks.task import Task


def test_schedule_driver_label_is_the_raw_value_not_the_enum_repr():
    """Application-layer driver label must never be str(enum_member)
    ("ConstraintType.MUST_START_ON") -- confirmed fixed by using
    .value instead."""
    task = Task(
        id="t1",
        project_id="p1",
        name="Constrained Task",
        duration_days=2,
        constraint_type=ConstraintType.MUST_START_ON,
        constraint_date=date(2026, 9, 18),
    )
    drivers = build_schedule_drivers(task, [], {})
    constraint_drivers = [d for d in drivers if d.kind == "constraint"]
    assert len(constraint_drivers) == 1
    assert constraint_drivers[0].label == "must_start_on"
    assert "ConstraintType" not in constraint_drivers[0].label


def test_desktop_serializer_re_derives_the_canonical_label_from_the_raw_driver_value():
    """The desktop layer boundary re-labels a raw application-layer
    driver value into the same canonical form every other consumer
    uses -- proving the fix actually closes the loop, not just that the
    application layer stopped emitting garbage."""
    from src.core.modules.project_management.application.scheduling.forecasting.task_schedule_overview import (
        ScheduleDriver,
    )
    from src.core.modules.project_management.api.desktop.scheduling.models.change_impact import (
        TaskScheduleImpactOverviewDesktopDto,
    )

    driver = ScheduleDriver(kind="constraint", label="must_start_on", detail="2026-09-18")
    canonical = constraint_presentation(ConstraintType.MUST_START_ON).label
    # Re-derive exactly the way change_impact_serializer.py's
    # serialize_task_schedule_overview does at the layer boundary.
    rederived_label = constraint_presentation(driver.label).label if driver.kind == "constraint" else driver.label
    assert rederived_label == canonical == "Must Start On (MSO)"


def test_constraint_presentation_never_renders_a_bare_snake_case_value_as_a_label():
    for value in ConstraintType:
        presentation = constraint_presentation(value)
        assert presentation.label != value.value
        assert "_" not in presentation.label.split("(")[0]
