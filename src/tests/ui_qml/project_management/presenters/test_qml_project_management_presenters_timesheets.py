from datetime import date, datetime
from src.core.modules.project_management.contracts.reads.sorting import ReadSort
from src.core.modules.project_management.contracts.reads.timesheets.review_reader import TimesheetReviewQueueFact, TimesheetReviewReadPage, TimesheetReviewInspectorFact
from src.core.platform.domain.time_management.time import TimesheetPeriodStatus
from types import SimpleNamespace

from src.ui_qml.modules.project_management.context import (
    ProjectManagementWorkspaceCatalog,
)


def _review_fact() -> TimesheetReviewQueueFact:
    return TimesheetReviewQueueFact(
        item_id="period-1", timesheet_period_id="period-1", version=1,
        resource_id="res-1", resource_name="Electrical Crew", resource_code="RES-1",
        period_start=date(2026, 5, 1), period_end=date(2026, 5, 31),
        status=TimesheetPeriodStatus.SUBMITTED,
        submitted_at=datetime(2026, 5, 4, 17), submitted_by_username="alex",
        decided_at=None, decided_by_username=None, decision_note=None,
        total_hours=16.0, project_count=1, task_count=1, entry_count=2,
        generic_entry_count=0, project_ids=("proj-1",),
    )


class _FakeTimesheetsDesktopApi:
    def __init__(self):
        self.review_queries = []

    def list_projects(self):
        return (
            SimpleNamespace(value="proj-1", label="Plant Upgrade"),
            SimpleNamespace(value="proj-2", label="Warehouse Retrofit"),
        )

    def list_assignments(self, *, project_id=None):
        rows = (
            SimpleNamespace(value="assign-1", label="Plant Upgrade | Cable Pull | Electrical Crew"),
            SimpleNamespace(value="assign-2", label="Warehouse Retrofit | Lighting Retrofit | Alex Taylor"),
        )
        if project_id == "proj-1":
            return rows[:1]
        if project_id == "proj-2":
            return rows[1:]
        return rows

    def list_queue_statuses(self):
        return (
            SimpleNamespace(value="all", label="All statuses"),
            SimpleNamespace(value="SUBMITTED", label="Submitted"),
            SimpleNamespace(value="APPROVED", label="Approved"),
        )

    def list_review_resources(self, *, project_id=None):
        rows = (
            SimpleNamespace(value="res-1", label="Electrical Crew"),
            SimpleNamespace(value="res-2", label="Alex Taylor"),
        )
        if project_id == "proj-1":
            return rows[:1]
        if project_id == "proj-2":
            return rows[1:]
        return rows


    def list_review_queue_page(
        self,
        *,
        status="SUBMITTED",
        search_text="",
        project_id=None,
        resource_id=None,
        period_start_from=None,
        period_start_to=None,
        page=1,
        page_size=25,
        sort_key="submittedAt",
        sort_direction="desc",
    ):
        self.review_queries.append(
            {
                "status": status,
                "search_text": search_text,
                "project_id": project_id,
                "resource_id": resource_id,
                "period_start_from": period_start_from,
                "period_start_to": period_start_to,
                "page": page,
                "page_size": page_size,
                "sort_key": sort_key,
                "sort_direction": sort_direction,
            }
        )
        return TimesheetReviewReadPage(items=(_review_fact(),), total=1,
            page=page, page_size=page_size, sort=ReadSort.normalize(
                key=sort_key, direction=sort_direction,
                allowed_keys={"title", "submittedAt"}, default_key="submittedAt"))

    def get_review_detail(self, period_id):
        assert period_id == "period-1"
        return TimesheetReviewInspectorFact(summary=_review_fact())


def test_project_management_workspace_catalog_exposes_typed_review_queue_controller() -> None:
    desktop_api = _FakeTimesheetsDesktopApi()
    catalog = ProjectManagementWorkspaceCatalog(
        desktop_api_registry=SimpleNamespace(
            project_management_timesheets=desktop_api
        )
    )

    controller = catalog.reviewQueueWorkspace

    assert controller.workspace["routeId"] == "project_management.timesheets"
    assert controller.overview["title"] == "Review Queue"
    assert not hasattr(controller, "assignmentOptions")
    assert not hasattr(controller, "entries")
    assert not hasattr(controller, "selectedEntry")
    assert controller.reviewQueue["items"][0]["title"] == "Electrical Crew | May 2026"

    controller.setQueueStatus("all")

    assert controller.selectedQueueStatus == "all"
    assert controller.selectedQueuePeriodId == ""
    assert controller.reviewDetail["title"] == "No review period selected"

    controller.setQueuePage(2)
    controller.setQueueSort("title", 0)

    assert controller.queuePage == 1
    assert controller.queueSortKey == "title"
    assert controller.queueSortDirection == 0
    assert desktop_api.review_queries[-1]["page"] == 1
    assert desktop_api.review_queries[-1]["sort_key"] == "title"
    assert desktop_api.review_queries[-1]["sort_direction"] == "asc"

    controller.setQueuePage(2)

    assert controller.queuePage == 2
    assert controller.queueSortKey == "title"
    assert controller.queueSortDirection == 0
    assert desktop_api.review_queries[-1]["page"] == 2
    assert desktop_api.review_queries[-1]["sort_key"] == "title"
    assert desktop_api.review_queries[-1]["sort_direction"] == "asc"
