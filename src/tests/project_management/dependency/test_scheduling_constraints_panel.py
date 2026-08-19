"""R4.4 constraint pass, Phase S: the Scheduling workspace's "Constraints"
panel for the selected activity previously fabricated rows that had
NOTHING to do with the task's real Task.constraint_type/constraint_date
-- a "Planned Start" row appeared whenever start_date was set (every
scheduled task, constrained or not), and Task.deadline was mislabeled as
"Finish No Later Than" even though Deadline is a distinct concept from
the real FINISH_NO_LATER_THAN constraint type (see
constraint_presentation.py's module docstring, and the R4.4 audit's
explicit product-model decision that Deadline must never be labeled as
FNLT). SchedulingTaskDto did not even carry the real constraint fields,
so the panel had no way to show them.

Fixed by: (1) threading constraint_type/constraint_type_label/
constraint_date onto SchedulingTaskDto via the two schedule item
serializers; (2) only reporting a "Constraints" row when a REAL
constraint is set, titled with its humanized label; (3) renaming the
deadline row from "Finish No Later Than" to plain "Deadline".
"""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from src.ui_qml.modules.project_management.presenters.scheduling.detail_builder import (
    build_constraints_collection,
)
from src.ui_qml.modules.project_management.presenters.scheduling.formatters import (
    constraint_label_for_activity,
)


def _activity(**overrides):
    base = dict(
        id="task-1",
        start_date=date(2026, 9, 7),
        deadline=None,
        actual_start=None,
        actual_end=None,
        constraint_type="",
        constraint_type_label="",
        constraint_date=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestBuildConstraintsCollection:
    def test_plain_start_date_with_no_constraint_reports_no_rows(self):
        """An ASAP-scheduled task (start_date computed by CPM, no explicit
        Task.constraint_type) must not be shown as if "Planned Start" were
        an active schedule control -- that was the original bug."""
        collection = build_constraints_collection(_activity())
        assert collection.items == ()

    def test_real_constraint_reports_its_humanized_label(self):
        activity = _activity(
            constraint_type="must_start_on",
            constraint_type_label="Must Start On (MSO)",
            constraint_date=date(2026, 9, 8),
        )
        collection = build_constraints_collection(activity)
        titles = [item.title for item in collection.items]
        assert titles == ["Must Start On (MSO)"]
        assert collection.items[0].subtitle == "2026-09-08"

    def test_deadline_is_labeled_deadline_not_finish_no_later_than(self):
        activity = _activity(deadline=date(2026, 9, 20))
        collection = build_constraints_collection(activity)
        titles = [item.title for item in collection.items]
        assert titles == ["Deadline"]
        assert "Finish No Later Than" not in titles
        assert "Finish No Later" not in titles[0]

    def test_real_constraint_and_deadline_both_report_as_distinct_rows(self):
        activity = _activity(
            constraint_type="start_no_earlier_than",
            constraint_type_label="Start No Earlier Than (SNET)",
            constraint_date=date(2026, 9, 8),
            deadline=date(2026, 9, 20),
        )
        collection = build_constraints_collection(activity)
        titles = [item.title for item in collection.items]
        assert titles == ["Start No Earlier Than (SNET)", "Deadline"]

    def test_actual_dates_still_report_as_execution_locks(self):
        activity = _activity(actual_start=date(2026, 9, 7), actual_end=date(2026, 9, 9))
        collection = build_constraints_collection(activity)
        titles = [item.title for item in collection.items]
        assert titles == ["Actual Start Lock", "Actual Finish Lock"]

    def test_none_selected_activity_returns_empty_state(self):
        collection = build_constraints_collection(None)
        assert collection.items == ()
        assert collection.empty_state


class TestConstraintLabelForActivity:
    def test_real_constraint_takes_precedence_over_deadline(self):
        activity = _activity(
            constraint_type="must_finish_on",
            constraint_type_label="Must Finish On (MFO)",
            deadline=date(2026, 9, 20),
        )
        assert constraint_label_for_activity(activity) == "Must Finish On (MFO)"

    def test_deadline_alone_reports_plain_deadline_label(self):
        activity = _activity(deadline=date(2026, 9, 20))
        assert constraint_label_for_activity(activity) == "Deadline"

    def test_actual_finish_takes_precedence_over_everything(self):
        activity = _activity(
            actual_end=date(2026, 9, 9),
            constraint_type="must_start_on",
            constraint_type_label="Must Start On (MSO)",
            deadline=date(2026, 9, 20),
        )
        assert constraint_label_for_activity(activity) == "Actual finish locked"

    def test_plain_start_date_with_no_controls_reports_planned_start_anchor(self):
        activity = _activity()
        assert constraint_label_for_activity(activity) == "Planned start anchor"


class TestSchedulingTaskDtoConstraintThreading:
    """End-to-end: a real MUST_START_ON task must surface its humanized
    constraint label through SchedulingTaskDto, not just at the domain
    layer."""

    def test_build_schedule_from_engine_threads_real_constraint_label(self, services):
        from src.core.modules.project_management.api.desktop.scheduling.services.scheduling_facade_service import (
            build_schedule_from_engine,
        )

        ps = services["project_service"]
        ts = services["task_service"]
        sched = services["scheduling_engine"]
        project = ps.create_project("Scheduling Panel Constraint Threading", "")
        task = ts.create_task(
            project.id,
            "Cable Pull",
            "",
            start_date=date(2026, 9, 7),
            duration_days=2,
            constraint_type="must_start_on",
            constraint_date=date(2026, 9, 7),
        )

        items = build_schedule_from_engine(project.id, sched, persist=False)
        item = next(i for i in items if i.id == task.id)

        assert item.constraint_type == "must_start_on"
        assert item.constraint_type_label == "Must Start On (MSO)"
        assert item.constraint_date == date(2026, 9, 7)

    def test_build_schedule_from_engine_reports_asap_for_unconstrained_task(self, services):
        from src.core.modules.project_management.api.desktop.scheduling.services.scheduling_facade_service import (
            build_schedule_from_engine,
        )

        ps = services["project_service"]
        ts = services["task_service"]
        sched = services["scheduling_engine"]
        project = ps.create_project("Scheduling Panel No Constraint", "")
        task = ts.create_task(
            project.id, "Untouched", "", start_date=date(2026, 9, 7), duration_days=2
        )

        items = build_schedule_from_engine(project.id, sched, persist=False)
        item = next(i for i in items if i.id == task.id)

        assert item.constraint_type == ""
