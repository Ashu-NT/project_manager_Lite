from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from src.core.modules.project_management.infrastructure.persistence.orm.task import TaskORM
from src.core.modules.project_management.domain.enums import TaskStatus
from src.tests.project_management._sql_measurement_helpers import measure_sql


def _seed_project(services, *, name: str = "Overview Scale Project"):
    today = date.today()
    return services["project_service"].create_project(
        name,
        start_date=today - timedelta(days=60),
        end_date=today + timedelta(days=60),
        financial_currency_code="EUR",
    )


def _seed_overdue_tasks(services, project_id: str, count: int, *, id_prefix: str = "task") -> None:
    today = date.today()
    rows = [
        TaskORM(
            id=f"{id_prefix}-{index:05d}",
            project_id=project_id,
            wbs_code=f"{id_prefix}-{index:05d}",
            sort_order=index,
            name=f"Overdue Task {index:05d}",
            status=TaskStatus.IN_PROGRESS,
            start_date=today - timedelta(days=30),
            end_date=today - timedelta(days=5),
            deadline=today - timedelta(days=5),
            percent_complete=40.0,
            version=1,
        )
        for index in range(count)
    ]
    services["session"].add_all(rows)
    services["session"].flush()


def _build_dashboard_api(services):
    from src.core.modules.project_management.api.desktop.dashboard.factories.dashboard_api_factory import (
        build_project_management_dashboard_desktop_api,
    )

    return build_project_management_dashboard_desktop_api(
        project_service=services["project_service"],
        dashboard_service=services["dashboard_service"],
        baseline_service=services["baseline_service"],
        reporting_service=services["reporting_service"],
        collaboration_service=services["collaboration_service"],
        task_service=services["task_service"],
    )


def test_delayed_tasks_page_reaches_page_two_and_total_is_authoritative(services) -> None:
    project = _seed_project(services)
    _seed_overdue_tasks(services, project.id, 25)
    api = _build_dashboard_api(services)

    page1 = api.list_delayed_tasks_page(project_id=project.id, page=1, page_size=10)
    page2 = api.list_delayed_tasks_page(project_id=project.id, page=2, page_size=10)
    page3 = api.list_delayed_tasks_page(project_id=project.id, page=3, page_size=10)

    assert page1.total_count == 25
    assert len(page1.rows) == 10
    assert len(page2.rows) == 10
    assert len(page3.rows) == 5
    ids_seen = {row.id for row in (*page1.rows, *page2.rows, *page3.rows)}
    assert len(ids_seen) == 25


def test_delayed_tasks_page_search_filters_before_pagination(services) -> None:
    project = _seed_project(services)
    _seed_overdue_tasks(services, project.id, 5)
    today = date.today()
    services["session"].add(
        TaskORM(
            id="task-findme",
            project_id=project.id,
            wbs_code="task-findme",
            sort_order=99,
            name="Uniquely Searchable Overdue Task",
            status=TaskStatus.IN_PROGRESS,
            end_date=today - timedelta(days=1),
            deadline=today - timedelta(days=1),
            version=1,
        )
    )
    services["session"].flush()
    api = _build_dashboard_api(services)

    result = api.list_delayed_tasks_page(project_id=project.id, search_text="Uniquely Searchable", page=1, page_size=10)

    assert result.total_count == 1
    assert result.rows[0].values["taskName"] == "Uniquely Searchable Overdue Task"


def test_delayed_tasks_page_all_projects_scope_does_not_require_project_id(services) -> None:
    project_a = _seed_project(services, name="Overview Scale Project A")
    project_b = _seed_project(services, name="Overview Scale Project B")
    _seed_overdue_tasks(services, project_a.id, 3, id_prefix="task-a")
    _seed_overdue_tasks(services, project_b.id, 4, id_prefix="task-b")
    api = _build_dashboard_api(services)

    result = api.list_delayed_tasks_page(project_id=None, page=1, page_size=50)

    assert result.total_count == 7
    project_ids_seen = {row.state["projectId"] for row in result.rows}
    assert project_ids_seen == {project_a.id, project_b.id}


def test_delayed_tasks_page_excludes_non_overdue_tasks(services) -> None:
    project = _seed_project(services)
    _seed_overdue_tasks(services, project.id, 2)
    today = date.today()
    services["session"].add(
        TaskORM(
            id="task-future",
            project_id=project.id,
            wbs_code="task-future",
            sort_order=50,
            name="Future Task",
            status=TaskStatus.TODO,
            end_date=today + timedelta(days=30),
            deadline=today + timedelta(days=30),
            version=1,
        )
    )
    services["session"].flush()
    api = _build_dashboard_api(services)

    result = api.list_delayed_tasks_page(project_id=project.id, page=1, page_size=50)

    assert result.total_count == 2
    assert all(row.values["taskName"] != "Future Task" for row in result.rows)


def test_delayed_tasks_page_scales_to_ten_thousand_rows_without_full_materialization(services) -> None:
    """Focused ~10,000-row characterization for the one collection classified
    SCALABLE. Proves only the requested page is materialized and the query
    count stays flat regardless of total row count."""
    project = _seed_project(services)
    _seed_overdue_tasks(services, project.id, 10_000)
    api = _build_dashboard_api(services)

    with measure_sql(services["session"]) as stats:
        page = api.list_delayed_tasks_page(project_id=project.id, page=1, page_size=25, sort_key="wbsCode", sort_direction="asc")
    assert page.total_count == 10_000
    assert len(page.rows) == 25
    assert stats.total_statements < 10

    with measure_sql(services["session"]) as stats_deep:
        deep_page = api.list_delayed_tasks_page(project_id=project.id, page=400, page_size=25, sort_key="wbsCode", sort_direction="asc")
    assert deep_page.total_count == 10_000
    assert len(deep_page.rows) == 25
    # Reaching page 400 costs the same query count as page 1 -- the server
    # never fetches/walks the skipped rows in Python.
    assert stats_deep.total_statements == stats.total_statements


def test_dashboard_portfolio_kpi_is_independent_of_delayed_tasks_page_state(services) -> None:
    """R3.7's Dashboard portfolio N+1 fix and the KPI aggregate it powers
    must stay independent of the new Delayed Tasks page/page_size -- a
    scalable operational tab must never change what the KPI strip shows."""
    project = _seed_project(services)
    _seed_overdue_tasks(services, project.id, 30)
    dashboard = services["dashboard_service"]
    api = _build_dashboard_api(services)

    before = dashboard.get_portfolio_data()
    api.list_delayed_tasks_page(project_id=project.id, page=1, page_size=5)
    api.list_delayed_tasks_page(project_id=project.id, page=3, page_size=5)
    after = dashboard.get_portfolio_data()

    assert before.portfolio.projects_total == after.portfolio.projects_total
    assert before.kpi.tasks_total == after.kpi.tasks_total
