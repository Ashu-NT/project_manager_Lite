from __future__ import annotations

from datetime import date, datetime

from src.core.application.global_overview.contracts.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterItemDto,
    ActionCenterSummaryDto,
)
from src.core.application.global_overview.services.action_center_service import (
    ActionCenterService,
)

_TODAY = date(2026, 9, 10)
_CONTEXT = ActionCenterContext(user_id="u1", tenant_id="t1", organization_id="o1")


class _FakeContributor:
    def __init__(self, contribution: ActionCenterContribution) -> None:
        self._contribution = contribution
        self.calls: list[int] = []

    def collect(self, context: ActionCenterContext, preview_limit: int) -> ActionCenterContribution:
        self.calls.append(preview_limit)
        return self._contribution


def _item(
    item_id: str,
    *,
    kind: str = "pm_task",
    module: str = "Project Management",
    due_at: date | None = None,
    source_timestamp: datetime | None = None,
) -> ActionCenterItemDto:
    return ActionCenterItemDto(
        id=item_id,
        kind=kind,
        title=f"Item {item_id}",
        module=module,
        subject_type="task",
        subject_id=item_id,
        subject_display="Subject",
        action_state="todo",
        route_id="project_management.tasks",
        due_at=due_at,
        source_timestamp=source_timestamp,
    )


def test_exact_summary_aggregation_sums_every_contributor():
    platform = _FakeContributor(
        ActionCenterContribution(
            items=(_item("a"),),
            summary=ActionCenterSummaryDto(
                all_action_items=5, reviews_and_approvals=5, assigned_work=0, submissions=0
            ),
        )
    )
    pm = _FakeContributor(
        ActionCenterContribution(
            items=(_item("b"),),
            summary=ActionCenterSummaryDto(
                all_action_items=7, reviews_and_approvals=1, assigned_work=4, submissions=2
            ),
        )
    )
    service = ActionCenterService(contributors=(platform, pm))

    result = service.build(_CONTEXT, preview_limit=50, today=_TODAY)

    assert result.summary == ActionCenterSummaryDto(
        all_action_items=12, reviews_and_approvals=6, assigned_work=4, submissions=2
    )


def test_bounded_candidate_merge_respects_the_global_preview_limit():
    platform = _FakeContributor(
        ActionCenterContribution(
            items=tuple(_item(f"p{i}") for i in range(5)),
            summary=ActionCenterSummaryDto(5, 5, 0, 0),
        )
    )
    pm = _FakeContributor(
        ActionCenterContribution(
            items=tuple(_item(f"m{i}") for i in range(5)),
            summary=ActionCenterSummaryDto(5, 0, 5, 0),
        )
    )
    service = ActionCenterService(contributors=(platform, pm))

    result = service.build(_CONTEXT, preview_limit=4, today=_TODAY)

    assert len(result.items) == 4
    # Summary is unaffected by the preview truncation.
    assert result.summary.all_action_items == 10


def test_summary_remains_exact_when_preview_is_truncated_to_zero():
    platform = _FakeContributor(
        ActionCenterContribution(
            items=(_item("a"), _item("b"), _item("c")),
            summary=ActionCenterSummaryDto(3, 3, 0, 0),
        )
    )
    service = ActionCenterService(contributors=(platform,))

    result = service.build(_CONTEXT, preview_limit=0, today=_TODAY)

    assert result.items == ()
    assert result.summary.all_action_items == 3


def test_deterministic_ordering_overdue_then_due_today_then_future_then_no_due_date():
    overdue = _item("overdue", due_at=date(2026, 9, 1))
    due_today = _item("today", due_at=_TODAY)
    future_soon = _item("soon", due_at=date(2026, 9, 12))
    future_later = _item("later", due_at=date(2026, 9, 20))
    no_due_newer = _item("newer", source_timestamp=datetime(2026, 9, 9, 10, 0))
    no_due_older = _item("older", source_timestamp=datetime(2026, 9, 1, 10, 0))
    no_due_unknown = _item("unknown")

    platform = _FakeContributor(
        ActionCenterContribution(
            items=(no_due_unknown, future_later, no_due_older),
            summary=ActionCenterSummaryDto(3, 3, 0, 0),
        )
    )
    pm = _FakeContributor(
        ActionCenterContribution(
            items=(due_today, no_due_newer, overdue, future_soon),
            summary=ActionCenterSummaryDto(4, 0, 4, 0),
        )
    )
    service = ActionCenterService(contributors=(platform, pm))

    result = service.build(_CONTEXT, preview_limit=10, today=_TODAY)

    assert [item.id for item in result.items] == [
        "overdue",
        "today",
        "soon",
        "later",
        "newer",
        "older",
        "unknown",
    ]


def test_contributor_registration_order_does_not_change_the_result():
    overdue = _item("overdue", due_at=date(2026, 9, 1))
    due_today = _item("today", due_at=_TODAY)

    platform = _FakeContributor(
        ActionCenterContribution(items=(overdue,), summary=ActionCenterSummaryDto(1, 1, 0, 0))
    )
    pm = _FakeContributor(
        ActionCenterContribution(items=(due_today,), summary=ActionCenterSummaryDto(1, 0, 1, 0))
    )

    forward = ActionCenterService(contributors=(platform, pm)).build(
        _CONTEXT, preview_limit=10, today=_TODAY
    )
    backward = ActionCenterService(contributors=(pm, platform)).build(
        _CONTEXT, preview_limit=10, today=_TODAY
    )

    assert [item.id for item in forward.items] == [item.id for item in backward.items]
    assert forward.summary == backward.summary


def test_each_contributor_is_asked_for_the_requested_preview_limit():
    platform = _FakeContributor(
        ActionCenterContribution(items=(), summary=ActionCenterSummaryDto(0, 0, 0, 0))
    )
    pm = _FakeContributor(
        ActionCenterContribution(items=(), summary=ActionCenterSummaryDto(0, 0, 0, 0))
    )
    service = ActionCenterService(contributors=(platform, pm))

    service.build(_CONTEXT, preview_limit=15, today=_TODAY)

    assert platform.calls == [15]
    assert pm.calls == [15]
