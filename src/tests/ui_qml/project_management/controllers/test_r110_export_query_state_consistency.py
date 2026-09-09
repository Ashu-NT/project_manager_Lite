from __future__ import annotations

from types import SimpleNamespace

from src.core.modules.project_management.api.desktop.financials.api import (
    ProjectManagementFinancialsDesktopApi,
)
from src.core.modules.project_management.application.common.pagination import (
    normalize_offset_for_total,
    normalize_page_for_total,
)
from src.ui_qml.modules.project_management.controllers.projects.project_selection_handler import (
    set_search_text as set_project_search_text,
)
from src.ui_qml.modules.project_management.controllers.resources.resource_selection_handler import (
    set_category_filter,
)
from src.ui_qml.modules.project_management.controllers.tasks.task_filter_actions import (
    set_status_filter as set_task_status_filter,
)
from src.ui_qml.modules.project_management.presenters.projects.projects_workspace_presenter import (
    ProjectProjectsWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.resources import (
    resources_workspace_presenter as resources_presenter_module,
)
from src.ui_qml.modules.project_management.presenters.resources.resources_workspace_presenter import (
    ProjectResourcesWorkspacePresenter,
)
from src.ui_qml.modules.project_management.presenters.tasks import (
    tasks_workspace_presenter as tasks_presenter_module,
)
from src.ui_qml.modules.project_management.presenters.tasks.tasks_workspace_presenter import (
    ProjectTasksWorkspacePresenter,
)


def test_pagination_normalization_clamps_empty_and_beyond_last_requests() -> None:
    assert normalize_page_for_total(page=8, page_size=25, total=0) == 1
    assert normalize_page_for_total(page=8, page_size=25, total=51) == 3
    assert normalize_offset_for_total(offset=500, limit=25, total=51) == 50


def test_projects_export_fetches_every_matching_page_with_authoritative_query() -> None:
    presenter = object.__new__(ProjectProjectsWorkspacePresenter)
    calls: list[dict[str, object]] = []

    def build_workspace_state(**kwargs):
        calls.append(kwargs)
        page = int(kwargs["page"])
        rows = ("project-a", "project-b") if page == 1 else ("project-c",)
        return SimpleNamespace(
            projects=rows,
            page_size=2,
            total_count=3,
        )

    presenter.build_workspace_state = build_workspace_state

    records = presenter.list_export_records(
        search_text="north",
        status_filter="active",
        sort_key="endDateLabel",
        sort_direction="desc",
        batch_size=2,
    )

    assert records == ("project-a", "project-b", "project-c")
    assert [call["page"] for call in calls] == [1, 2]
    assert all(call["search_text"] == "north" for call in calls)
    assert all(call["status_filter"] == "active" for call in calls)
    assert all(call["sort_key"] == "endDateLabel" for call in calls)
    assert all(call["sort_direction"] == "desc" for call in calls)


class _PagedDesktopApi:
    def __init__(self, method_name: str) -> None:
        self.calls: list[dict[str, object]] = []
        setattr(self, method_name, self._list_page)

    def _list_page(self, **kwargs):
        self.calls.append(kwargs)
        page = int(kwargs["page"])
        rows = ("row-a", "row-b") if page == 1 else ("row-c",)
        return SimpleNamespace(
            items=rows,
            filtered_total=3,
            page=page,
            page_size=2,
        )


def test_tasks_export_fetches_all_pages_with_project_filters_and_sort(monkeypatch) -> None:
    api = _PagedDesktopApi("list_task_page")
    presenter = object.__new__(ProjectTasksWorkspacePresenter)
    presenter._desktop_api = api
    monkeypatch.setattr(
        tasks_presenter_module,
        "to_task_record_view_model",
        lambda item: item,
    )

    records = presenter.list_export_records(
        project_id="project-1",
        search_text="permit",
        status_filter="blocked",
        priority_filter="high",
        schedule_filter="overdue",
        sort_key="endDateLabel",
        sort_direction="desc",
        batch_size=2,
    )

    assert records == ("row-a", "row-b", "row-c")
    assert [call["page"] for call in api.calls] == [1, 2]
    assert all(call["project_id"] == "project-1" for call in api.calls)
    assert all(call["status"] == "blocked" for call in api.calls)
    assert all(call["priority"] == "high" for call in api.calls)
    assert all(call["schedule"] == "overdue" for call in api.calls)
    assert all(call["sort_direction"] == "desc" for call in api.calls)


def test_resources_export_fetches_all_pages_with_filters_and_sort(monkeypatch) -> None:
    api = _PagedDesktopApi("list_resource_page")
    presenter = object.__new__(ProjectResourcesWorkspacePresenter)
    presenter._desktop_api = api
    monkeypatch.setattr(
        resources_presenter_module,
        "to_resource_record_view_model",
        lambda item: item,
    )

    records = presenter.list_export_records(
        search_text="planner",
        active_filter="active",
        category_filter="LABOR",
        sort_key="utilizationValue",
        sort_direction="desc",
        batch_size=2,
    )

    assert records == ("row-a", "row-b", "row-c")
    assert [call["page"] for call in api.calls] == [1, 2]
    assert all(call["search_text"] == "planner" for call in api.calls)
    assert all(call["active"] == "active" for call in api.calls)
    assert all(call["category"] == "LABOR" for call in api.calls)
    assert all(call["sort_key"] == "utilizationValue" for call in api.calls)


class _QueryController:
    def __init__(self) -> None:
        self._search_text = ""
        self._selected_status_filter = "all"
        self._selected_category_filter = "ALL"
        self._project_page = 4
        self._task_page = 4
        self._resource_page = 4
        self.page_notifications: list[tuple[str, int]] = []
        self.refresh_count = 0

    def _set_search_text(self, value: str) -> None:
        self._search_text = value

    def _set_selected_status_filter(self, value: str) -> None:
        self._selected_status_filter = value

    def _set_selected_category_filter(self, value: str) -> None:
        self._selected_category_filter = value

    def _set_selected_task_view_name(self, _value: str) -> None:
        pass

    def _set_project_page(self, value: int) -> None:
        self._project_page = value
        self.page_notifications.append(("project", value))

    def _set_task_page(self, value: int) -> None:
        self._task_page = value
        self.page_notifications.append(("task", value))

    def _set_resource_page(self, value: int) -> None:
        self._resource_page = value
        self.page_notifications.append(("resource", value))

    def refresh(self) -> None:
        self.refresh_count += 1


def test_query_changes_reset_page_through_notifying_setter_and_fetch_once() -> None:
    projects = _QueryController()
    set_project_search_text(projects, "  alpha  ")
    assert projects._search_text == "alpha"
    assert projects.page_notifications == [("project", 1)]
    assert projects.refresh_count == 1

    tasks = _QueryController()
    set_task_status_filter(tasks, " BLOCKED ")
    assert tasks._selected_status_filter == "blocked"
    assert tasks.page_notifications == [("task", 1)]
    assert tasks.refresh_count == 1

    resources = _QueryController()
    set_category_filter(resources, " labor ")
    assert resources._selected_category_filter == "LABOR"
    assert resources.page_notifications == [("resource", 1)]
    assert resources.refresh_count == 1


class _OffsetService:
    def __init__(self) -> None:
        self.calls: list[int] = []

    def list_for_project(self, _project_id: str, **kwargs):
        self.calls.append(int(kwargs["offset"]))
        return [], 3


def test_finance_actual_and_commitment_queries_return_normalized_offset() -> None:
    actuals = _OffsetService()
    commitments = _OffsetService()
    api = ProjectManagementFinancialsDesktopApi(
        cost_entry_service=actuals,
        commitment_service=commitments,
    )

    actual_page = api.list_cost_entries("project-1", offset=500, limit=2)
    commitment_page = api.list_commitments("project-1", offset=500, limit=2)

    assert actuals.calls == [500, 2]
    assert commitments.calls == [500, 2]
    assert actual_page.offset == 2
    assert commitment_page.offset == 2


def test_valid_non_page_boundary_offset_is_preserved() -> None:
    assert normalize_offset_for_total(offset=10, limit=20, total=50) == 10
