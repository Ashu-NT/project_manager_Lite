from dataclasses import replace
from datetime import date

import pytest

from src.core.global_overview.application.action_center_service import (
    ActionCenterService,
)
from src.core.global_overview.application.ordering import (
    _sort_key,
    sort_action_center_items,
)
from src.core.global_overview.contract.action_center import (
    ActionCenterContext,
    ActionCenterContribution,
    ActionCenterItemDto,
    ActionCenterSummaryDto,
)

CONTEXT = ActionCenterContext("user", "tenant", "org")


class Contributor:
    def __init__(self, prefix, count):
        self.items = tuple(ActionCenterItemDto(id=f"{prefix}-{index:04d}", kind="work", title="Work", module=prefix,
            subject_type="task", subject_id=str(index), subject_display="Task", action_state="todo", route_id="workspace") for index in range(count))
        self.limits = []

    def collect(self, context, limit, *, after=None):
        self.limits.append(limit)
        ordered = sort_action_center_items(self.items, today=date.today())
        if after:
            ordered = tuple(item for item in ordered if _sort_key(item, today=date.today()) > _sort_key(after, today=date.today()))
        return ActionCenterContribution(ordered[:limit], ActionCenterSummaryDto(len(self.items), 0, len(self.items), 0))


@pytest.mark.parametrize("counts", [(0,), (17,), (50, 1), (0, 27), (13, 13)])
def test_global_cursor_has_no_gaps_duplicates_and_bounds_every_contributor(counts):
    contributors = tuple(Contributor(str(index), count) for index, count in enumerate(counts))
    service = ActionCenterService(contributors=contributors)
    cursor = None
    seen = []
    while True:
        page = service.build(CONTEXT, preview_limit=10, after=cursor)
        assert len(page.items) <= 10
        assert page.summary.all_action_items == sum(counts)
        seen.extend(item.id for item in page.items)
        cursor = page.next_cursor
        if cursor is None:
            break
    assert len(set(seen)) == len(seen) == sum(counts)
    assert all(set(source.limits) == {11} for source in contributors)


def test_foreign_cursor_is_rejected_and_duplicate_ownership_is_not_hidden():
    source = Contributor("PM", 20)
    service = ActionCenterService(contributors=(source,))
    cursor = service.build(CONTEXT, preview_limit=10).next_cursor
    with pytest.raises(ValueError, match="different user or scope"):
        service.build(replace(CONTEXT, organization_id="foreign"), after=cursor)
    with pytest.raises(ValueError, match="Duplicate Action Center ownership"):
        ActionCenterService(contributors=(source, source)).build(CONTEXT)


def test_contributor_failure_is_not_reported_as_empty():
    class Broken:
        def collect(self, *args, **kwargs):
            raise RuntimeError("database unavailable")
    with pytest.raises(RuntimeError, match="database unavailable"):
        ActionCenterService(contributors=(Broken(),)).build(CONTEXT)


def test_disabled_pm_does_not_query_reader_and_rechecks_access_each_time():
    from src.core.modules.project_management.application.global_overview.pm_action_center_contributor import (
        ProjectManagementActionCenterContributor,
    )

    source = Contributor("PM", 1)
    enabled = False
    contributor = ProjectManagementActionCenterContributor(reader=source, is_accessible=lambda: enabled)
    assert contributor.collect(CONTEXT, 10).summary.all_action_items == 0
    assert source.limits == []
    enabled = True
    assert contributor.collect(CONTEXT, 10).summary.all_action_items == 1
    enabled = False
    assert contributor.collect(CONTEXT, 10).items == ()
    assert source.limits == [10]
