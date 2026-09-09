from __future__ import annotations

import pytest

from src.ui_qml.modules.project_management.presenters.scheduling.schedule_sort import (
    normalize_schedule_sort,
)


@pytest.mark.parametrize(
    "key",
    [
        "wbs",
        "taskName",
        "start",
        "finish",
        "duration",
        "remainingDuration",
        "float",
        "critical",
        "constraint",
        "progress",
        "status",
    ],
)
def test_schedule_sort_intent_accepts_supported_gantt_keys(key: str) -> None:
    resolved = normalize_schedule_sort(key=key, direction="desc")

    assert resolved.key == key
    assert resolved.direction.value == "desc"


def test_schedule_sort_intent_fails_safe_to_hierarchy_order() -> None:
    resolved = normalize_schedule_sort(key="arbitrary_code", direction="desc")

    assert resolved.key == "schedule"
    assert resolved.direction.value == "asc"
