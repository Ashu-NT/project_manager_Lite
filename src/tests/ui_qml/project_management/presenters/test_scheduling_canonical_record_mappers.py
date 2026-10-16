from datetime import date
from unittest.mock import Mock

import pytest

from src.core.modules.project_management.application.dashboard.models.report_models import (
    ResourceLoadRow,
)
from src.core.modules.project_management.application.scheduling.cpm.constraint_validator import (
    ConstraintViolation,
)
from src.core.modules.project_management.application.scheduling.models.leveling import (
    LevelingProposal,
    ProposedTaskMove,
    UnresolvedConflict,
)
from src.core.modules.project_management.domain.enums import ConstraintType
from src.ui_qml.modules.project_management.presenters.scheduling.leveling_builder import (
    build_resource_leveling_state,
)
from src.ui_qml.modules.project_management.presenters.scheduling.record_mappers import (
    to_constraint_violation_record,
    to_resource_load_record,
)


@pytest.mark.parametrize(
    ("utilization", "status"),
    [(0.0, "Idle"), (50.0, "Stable"), (85.0, "Hot"), (100.0, "Hot"), (120.0, "Overloaded")],
)
def test_resource_presenter_formats_canonical_facts(utilization: float, status: str) -> None:
    row = ResourceLoadRow("resource-1", "Ada", 96.0, 3, 80.0, utilization)

    record = to_resource_load_record(row)

    assert record.status_label == status
    assert record.subtitle == f"Utilization {utilization:.1f}% | Capacity 80.0%"
    assert record.supporting_text == "Peak allocation 96.0% across 3 task(s)"
    assert record.state == {
        "resourceId": "resource-1", "resourceName": "Ada",
        "allocationLabel": "96.0%", "capacityLabel": "80.0%",
        "utilizationLabel": f"{utilization:.1f}%", "tasksCount": 3, "statusLabel": status,
    }


@pytest.mark.parametrize(
    ("constraint_type", "severity", "label"),
    [
        (ConstraintType.DEADLINE, "hard", "Deadline"),
        (ConstraintType.START_NO_EARLIER_THAN, "soft", "Start No Earlier Than (SNET)"),
    ],
)
def test_constraint_presenter_formats_canonical_facts(
    constraint_type: ConstraintType, severity: str, label: str,
) -> None:
    violation = ConstraintViolation(
        "task-1", "Execution", constraint_type,
        date(2026, 5, 4), date(2026, 5, 6), "Date mismatch", 2,
    )

    record = to_constraint_violation_record(violation)

    assert record.id == f"task-1:{constraint_type.value}"
    assert record.status_label == f"{severity.title()} Constraint"
    assert record.subtitle == f"{label} | Required 2026-05-04"
    assert record.supporting_text == "Computed 2026-05-06 | Overrun 2d"
    assert record.state["constraintType"] == constraint_type.value
    assert record.state["severity"] == severity
    assert record.meta_text == "Date mismatch"


def test_leveling_presenter_formats_the_canonical_immutable_proposal() -> None:
    move = ProposedTaskMove(
        task_id="task-1", task_name="Execution", wbs_code="1.1",
        old_start=date(2026, 5, 4), old_finish=date(2026, 5, 5),
        new_start=date(2026, 5, 6), new_finish=date(2026, 5, 7),
        shift_working_days=2, reason="Resource capacity", resource_ids=("resource-1",),
        resource_names=("Ada",), float_before=3, float_after=1, critical_before=False,
        critical_after=False, infeasible_after=False,
    )
    conflict = UnresolvedConflict("resource-2", "Grace", date(2026, 5, 4), 130.0, "Pinned tasks")
    proposal = LevelingProposal(
        "project-1", "snapshot-1", False, 2, 1, (move,), (conflict,),
        date(2026, 5, 5), date(2026, 5, 7), False, (), ("Pinned tasks remain",),
    )
    api = Mock()
    api.preview_resource_leveling.return_value = proposal

    state = build_resource_leveling_state(api, " project-1 ")

    assert state["scheduleFingerprint"] == proposal.schedule_fingerprint
    assert state["projectFinishBeforeLabel"] == "May 05, 2026"
    assert state["projectFinishAfterLabel"] == "May 07, 2026"
    assert state["moves"][0]["shiftLabel"] == "May 04, 2026 -> May 06, 2026 (+2d)"
    assert state["moves"][0]["resourcesLabel"] == "Ada"
    assert state["moves"][0]["statusLabel"] == "Resolved"
    assert state["unresolvedConflicts"][0]["conflictDateLabel"] == "May 04, 2026"
    assert state["unresolvedConflicts"][0]["totalAllocationLabel"] == "130%"
    assert state["warnings"] == ["Pinned tasks remain"]
