from __future__ import annotations

from datetime import date

from sqlalchemy import event

from src.core.modules.project_management.domain.enums import (
    CostType,
    ProjectStatus,
    TaskStatus,
    WorkerType,
)
from src.core.modules.project_management.domain.risk.register import (
    RegisterEntrySeverity,
    RegisterEntryStatus,
    RegisterEntryType,
)


def test_project_catalog_filters_counts_and_pages_in_database(services) -> None:
    project_service = services["project_service"]
    alpha = project_service.create_project("Alpha Delivery", client_name="Northwind")
    beta = project_service.create_project("Beta Upgrade", client_name="Contoso")
    project_service.set_status(beta.id, ProjectStatus.ACTIVE)

    first_page = project_service.query_catalog_page(page=1, page_size=1)
    second_page = project_service.query_catalog_page(page=2, page_size=1)
    search_page = project_service.query_catalog_page(
        search_text="northwind",
        page=1,
        page_size=25,
    )

    assert first_page.filtered_total == 2
    assert first_page.summary.total == 2
    assert first_page.summary.active == 1
    assert first_page.summary.planned == 1
    assert first_page.items[0].project.id == alpha.id
    assert second_page.items[0].project.id == beta.id
    assert search_page.filtered_total == 1
    assert search_page.items[0].project.id == alpha.id


def test_project_catalog_sort_is_authoritative_across_pages(services) -> None:
    project_service = services["project_service"]
    alpha = project_service.create_project("Alpha Sort")
    beta = project_service.create_project("Beta Sort")
    gamma = project_service.create_project("Gamma Sort")

    descending_first = project_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=1, page_size=2
    )
    descending_second = project_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=2, page_size=2
    )
    unsupported = project_service.query_catalog_page(
        sort_key="arbitrary_sql", sort_direction="desc", page=1, page_size=3
    )

    assert [row.project.id for row in descending_first.items] == [gamma.id, beta.id]
    assert [row.project.id for row in descending_second.items] == [alpha.id]
    assert descending_first.sort.key == "title"
    assert descending_first.sort.direction.value == "desc"
    assert [row.project.id for row in unsupported.items] == [alpha.id, beta.id, gamma.id]
    assert unsupported.sort.key == "title"
    assert unsupported.sort.direction.value == "asc"


def test_task_workspace_pages_effective_wbs_rollups_before_filtering(services) -> None:
    project_service = services["project_service"]
    task_service = services["task_service"]
    project = project_service.create_project("WBS Database Paging")
    root = task_service.create_task(
        project.id,
        "Summary Delivery",
        start_date=date(2026, 5, 1),
        duration_days=5,
        status=TaskStatus.TODO,
        wbs_code="1",
    )
    child = task_service.create_task(
        project.id,
        "Blocked Work Package",
        start_date=date(2026, 5, 2),
        duration_days=2,
        status=TaskStatus.BLOCKED,
        priority=95,
        parent_task_id=root.id,
        wbs_code="1.1",
    )

    first_page = task_service.query_workspace_page(
        project_id=project.id,
        status="BLOCKED",
        page=1,
        page_size=1,
        as_of=date(2026, 5, 1),
    )
    second_page = task_service.query_workspace_page(
        project_id=project.id,
        status="BLOCKED",
        page=2,
        page_size=1,
        as_of=date(2026, 5, 1),
    )
    priority_page = task_service.query_workspace_page(
        search_text="priority>=90",
        page=1,
        page_size=25,
        as_of=date(2026, 5, 1),
    )

    assert first_page.filtered_total == 2
    assert first_page.summary.total == 2
    assert first_page.summary.blocked == 2
    assert first_page.items[0].id == root.id
    assert first_page.items[0].is_summary is True
    assert first_page.items[0].child_count == 1
    assert second_page.items[0].id == child.id
    assert second_page.items[0].hierarchy_depth == 1
    assert [item.id for item in priority_page.items] == [child.id]


def test_task_workspace_sort_is_authoritative_across_pages(services) -> None:
    project = services["project_service"].create_project("Task Sort Project")
    task_service = services["task_service"]
    alpha = task_service.create_task(project.id, "Alpha Task", wbs_code="1")
    beta = task_service.create_task(project.id, "Beta Task", wbs_code="2")
    gamma = task_service.create_task(project.id, "Gamma Task", wbs_code="3")

    first = task_service.query_workspace_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="desc",
        page=1,
        page_size=2,
    )
    second = task_service.query_workspace_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="desc",
        page=2,
        page_size=2,
    )
    unsupported = task_service.query_workspace_page(
        project_id=project.id,
        sort_key="unsafe_sql",
        sort_direction="desc",
        page=1,
        page_size=3,
    )

    assert [row.id for row in first.items] == [gamma.id, beta.id]
    assert [row.id for row in second.items] == [alpha.id]
    assert first.sort.direction.value == "desc"
    assert [row.id for row in unsupported.items] == [alpha.id, beta.id, gamma.id]
    assert unsupported.sort.key == "wbsCode"
    assert unsupported.sort.direction.value == "asc"


def test_resource_catalog_filters_aggregates_and_pages_in_database(services) -> None:
    resource_service = services["resource_service"]
    employee = services["employee_service"].create_employee(
        employee_code="EMP-RPAGE",
        full_name="Alex Database",
        title="Planner",
        department="Delivery",
        site_name="Berlin",
        email="alex.database@example.com",
    )
    employee_resource = resource_service.create_resource(
        name="Alex Database",
        role="Planner",
        worker_type=WorkerType.EMPLOYEE,
        employee_id=employee.id,
        capacity_percent=80.0,
        cost_type=CostType.LABOR,
    )
    vendor_resource = resource_service.create_resource(
        name="Vendor Crane",
        role="Equipment Operator",
        worker_type=WorkerType.EXTERNAL,
        capacity_percent=120.0,
        cost_type=CostType.EQUIPMENT,
        is_active=False,
    )

    first_page = resource_service.query_catalog_page(page=1, page_size=1)
    second_page = resource_service.query_catalog_page(page=2, page_size=1)
    employee_search = resource_service.query_catalog_page(
        search_text="delivery",
        page=1,
        page_size=25,
    )
    inactive_equipment = resource_service.query_catalog_page(
        active=False,
        category=CostType.EQUIPMENT,
        page=1,
        page_size=25,
    )

    assert first_page.summary.total == 2
    assert first_page.summary.active == 1
    assert first_page.summary.employees == 1
    assert first_page.summary.external == 1
    assert first_page.summary.average_capacity == 100.0
    assert first_page.items[0].resource.id == employee_resource.id
    assert second_page.items[0].resource.id == vendor_resource.id
    assert employee_search.items[0].department_label == "Delivery"
    assert inactive_equipment.filtered_total == 1
    assert inactive_equipment.items[0].resource.id == vendor_resource.id


def test_resource_catalog_sort_is_authoritative_across_pages(services) -> None:
    resource_service = services["resource_service"]
    alpha = resource_service.create_resource(name="Alpha Resource", role="Planner")
    beta = resource_service.create_resource(name="Beta Resource", role="Planner")
    gamma = resource_service.create_resource(name="Gamma Resource", role="Planner")

    first = resource_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=1, page_size=2
    )
    second = resource_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=2, page_size=2
    )
    unsupported = resource_service.query_catalog_page(
        sort_key="unsafe_sql", sort_direction="desc", page=1, page_size=3
    )

    assert [row.resource.id for row in first.items] == [gamma.id, beta.id]
    assert [row.resource.id for row in second.items] == [alpha.id]
    assert first.sort.direction.value == "desc"
    assert [row.resource.id for row in unsupported.items] == [alpha.id, beta.id, gamma.id]
    assert unsupported.sort.key == "catalog"
    assert unsupported.sort.direction.value == "asc"


def test_register_catalog_filters_urgent_queue_and_pages_in_database(services) -> None:
    project = services["project_service"].create_project("Register Database Paging")
    register_service = services["register_service"]
    critical_risk = register_service.create_entry(
        project.id,
        entry_type=RegisterEntryType.RISK,
        title="Critical supplier delay",
        severity=RegisterEntrySeverity.CRITICAL,
        status=RegisterEntryStatus.OPEN,
        due_date=date(2026, 5, 1),
    )
    issue = register_service.create_entry(
        project.id,
        entry_type=RegisterEntryType.ISSUE,
        title="Permit issue",
        severity=RegisterEntrySeverity.HIGH,
        status=RegisterEntryStatus.IN_PROGRESS,
        due_date=date(2026, 5, 3),
    )
    change = register_service.create_entry(
        project.id,
        entry_type=RegisterEntryType.CHANGE,
        title="Approved scope change",
        severity=RegisterEntrySeverity.MEDIUM,
        status=RegisterEntryStatus.CLOSED,
    )

    first_page = register_service.query_catalog_page(
        project_id=project.id,
        as_of=date(2026, 5, 10),
        page=1,
        page_size=1,
    )
    second_page = register_service.query_catalog_page(
        project_id=project.id,
        as_of=date(2026, 5, 10),
        page=2,
        page_size=1,
    )
    risks = register_service.query_catalog_page(
        project_id=project.id,
        entry_type=RegisterEntryType.RISK,
        search_text="supplier",
        as_of=date(2026, 5, 10),
        page=1,
        page_size=25,
    )

    assert first_page.filtered_total == 3
    assert first_page.summary.scope_total == 3
    assert first_page.summary.scope_risk_total == 1
    assert first_page.summary.open_risks == 1
    assert first_page.summary.open_issues == 1
    assert first_page.summary.pending_changes == 0
    assert first_page.summary.overdue == 2
    assert first_page.items[0].entry.id == critical_risk.id
    assert second_page.items[0].entry.id == issue.id
    assert [item.entry.id for item in first_page.urgent_items] == [
        critical_risk.id,
        issue.id,
    ]
    assert [item.entry.id for item in risks.items] == [critical_risk.id]
    assert change.id not in {item.entry.id for item in first_page.urgent_items}


def test_register_catalog_sort_is_authoritative_across_pages(services) -> None:
    project = services["project_service"].create_project("Register Sort Project")
    register_service = services["register_service"]
    alpha = register_service.create_entry(
        project.id,
        entry_type=RegisterEntryType.RISK,
        title="Alpha Register Entry",
        severity=RegisterEntrySeverity.LOW,
    )
    beta = register_service.create_entry(
        project.id,
        entry_type=RegisterEntryType.ISSUE,
        title="Beta Register Entry",
        severity=RegisterEntrySeverity.MEDIUM,
    )
    gamma = register_service.create_entry(
        project.id,
        entry_type=RegisterEntryType.CHANGE,
        title="Gamma Register Entry",
        severity=RegisterEntrySeverity.HIGH,
    )

    first = register_service.query_catalog_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="desc",
        page=1,
        page_size=2,
    )
    second = register_service.query_catalog_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="desc",
        page=2,
        page_size=2,
    )
    unsupported = register_service.query_catalog_page(
        project_id=project.id,
        sort_key="unsafe_sql",
        sort_direction="desc",
        page=1,
        page_size=3,
    )

    assert [row.entry.id for row in first.items] == [gamma.id, beta.id]
    assert [row.entry.id for row in second.items] == [alpha.id]
    assert first.sort.direction.value == "desc"
    assert unsupported.sort.key == "triage"
    assert unsupported.sort.direction.value == "asc"


def test_timesheet_review_queue_aggregates_and_pages_in_database(services) -> None:
    project = services["project_service"].create_project("Timesheet Database Paging")
    task = services["task_service"].create_task(
        project.id,
        "Database review task",
        start_date=date(2026, 6, 1),
        duration_days=5,
    )
    resource = services["resource_service"].create_resource(
        name="Database Reviewer",
        role="Engineer",
    )
    assignment = services["task_service"].assign_resource(
        task.id,
        resource.id,
        allocation_percent=100.0,
    )
    timesheets = services["timesheet_service"]
    timesheets.add_time_entry(
        assignment.id,
        entry_date=date(2026, 6, 2),
        hours=7.5,
        note="Database-backed review",
    )
    submitted = timesheets.submit_timesheet_period(
        resource.id,
        period_start=date(2026, 6, 1),
    )

    page = timesheets.query_review_queue_page(page=1, page_size=1)

    assert page.total == 1
    assert page.page == 1
    assert page.page_size == 1
    assert page.items[0].period_id == submitted.period_id
    assert page.items[0].resource_name == "Database Reviewer"
    assert page.items[0].entry_count == 1
    assert page.items[0].total_hours == 7.5
    assert page.items[0].project_ids == (project.id,)


def test_workspace_page_query_budgets_are_constant(services) -> None:
    session = services["project_service"]._session
    engine = session.get_bind()
    statement_count = 0

    def count_statement(*_args, **_kwargs) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        budgets = []
        for query in (
            lambda: services["project_service"].query_catalog_page(),
            lambda: services["task_service"].query_workspace_page(),
            lambda: services["resource_service"].query_catalog_page(),
            lambda: services["register_service"].query_catalog_page(),
            lambda: services["timesheet_service"].query_review_queue_page(),
        ):
            statement_count = 0
            query()
            budgets.append(statement_count)
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    # One statement is the shared module/entitlement guard; the remainder are
    # fixed aggregate/count/page reads and never scale with result cardinality.
    assert budgets == [4, 4, 4, 5, 3]
