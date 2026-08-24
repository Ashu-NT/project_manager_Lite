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


def test_project_catalog_site_department_manager_and_date_filters_compose(services) -> None:
    project_service = services["project_service"]
    site_service = services["site_service"]
    department_service = services["department_service"]
    # A real FK-valid user id (manager_user_id references users.id) -- the
    # admin principal authenticated by the `services` fixture.
    manager_id = services["user_session"].principal.user_id

    site_a = site_service.create_site(site_code="SITE-A", name="Hamburg Yard")
    site_b = site_service.create_site(site_code="SITE-B", name="Rotterdam Yard")
    dept_a = department_service.create_department(department_code="DEPT-A", name="Engineering")
    dept_b = department_service.create_department(department_code="DEPT-B", name="Operations")

    match = project_service.create_project(
        "Hamburg Refit",
        site_id=site_a.id,
        department_id=dept_a.id,
        manager_user_id=manager_id,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 6, 30),
    )
    project_service.create_project(
        "Rotterdam Refit",
        site_id=site_b.id,
        department_id=dept_a.id,
        manager_user_id=manager_id,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 6, 30),
    )
    project_service.create_project(
        "Hamburg Other Dept No Manager",
        site_id=site_a.id,
        department_id=dept_b.id,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 6, 30),
    )
    project_service.create_project(
        "Hamburg Out Of Range",
        site_id=site_a.id,
        department_id=dept_a.id,
        manager_user_id=manager_id,
        start_date=date(2027, 1, 10),
        end_date=date(2027, 6, 30),
    )

    # Site alone narrows to the three Hamburg-site projects (excludes Rotterdam).
    site_only = project_service.query_catalog_page(site_id=site_a.id, page=1, page_size=25)
    assert site_only.filtered_total == 3
    assert {row.project.site_id for row in site_only.items} == {site_a.id}

    # Manager alone excludes the unassigned "Other Dept" project.
    manager_only = project_service.query_catalog_page(
        manager_user_id=manager_id, page=1, page_size=25
    )
    assert manager_only.filtered_total == 3
    assert all(row.project.manager_user_id == manager_id for row in manager_only.items)

    # Site + department + manager + start-date range together return exactly
    # the single project matching the full intersection.
    composed = project_service.query_catalog_page(
        site_id=site_a.id,
        department_id=dept_a.id,
        manager_user_id=manager_id,
        start_date_from=date(2026, 1, 1),
        start_date_to=date(2026, 12, 31),
        page=1,
        page_size=25,
    )
    assert composed.filtered_total == 1
    assert composed.items[0].project.id == match.id

    # Department alone still returns both dept_a projects across sites.
    department_only = project_service.query_catalog_page(
        department_id=dept_a.id, page=1, page_size=25
    )
    assert department_only.filtered_total == 3

    # A start-date range excluding the out-of-range project proves the range
    # predicate is applied, not merely accepted and ignored.
    date_ranged = project_service.query_catalog_page(
        department_id=dept_a.id,
        start_date_from=date(2026, 1, 1),
        start_date_to=date(2026, 12, 31),
        page=1,
        page_size=25,
    )
    assert date_ranged.filtered_total == 2
    assert all(row.project.start_date.year == 2026 for row in date_ranged.items)


def test_project_resource_activity_is_queryable_by_parent_project_id(services) -> None:
    project_service = services["project_service"]
    resource_service = services["resource_service"]
    project_resource_service = services["project_resource_service"]
    activity_service = services["activity_service"]

    project_a = project_service.create_project("Parent Entity Activity A")
    project_b = project_service.create_project("Parent Entity Activity B")
    resource = resource_service.create_resource("Parent Entity Test Resource", "Planner")

    project_resource_service.add_to_project(
        project_id=project_a.id, resource_id=resource.id, planned_hours=10,
    )
    project_resource_service.add_to_project(
        project_id=project_b.id, resource_id=resource.id, planned_hours=5,
    )

    # Scoping by parent_entity_id must return only project_a's resource
    # activity, not project_b's -- proves the real column-backed filter
    # (not the shared workspace_id, which every entity in that project
    # uses) actually narrows correctly.
    entries_a = activity_service.list_recent(
        entity_type="project_resource", parent_entity_id=project_a.id,
    )
    assert len(entries_a) == 1
    assert entries_a[0].action == "project_resource.add"

    entries_b = activity_service.list_recent(
        entity_type="project_resource", parent_entity_id=project_b.id,
    )
    assert len(entries_b) == 1
    assert entries_b[0].id != entries_a[0].id

    # The presenter layer never talks to `activity_service` directly -- it
    # goes through `PlatformActivityDesktopApi`, a separate facade that
    # must forward every kwarg the service supports. It didn't forward
    # `parent_entity_id` at all (a real, shipped bug: the two layers'
    # signatures had drifted apart), which the assertions above -- calling
    # the service directly -- could not have caught.
    from src.core.platform.api.desktop.history.activity.activity import (
        PlatformActivityDesktopApi,
    )

    activity_api = PlatformActivityDesktopApi(activity_service=activity_service)
    result_a = activity_api.list_recent(
        entity_type="project_resource", parent_entity_id=project_a.id,
    )
    assert result_a.ok, result_a.error
    assert len(result_a.data) == 1


def test_project_catalog_project_name_and_client_name_filters_compose(services) -> None:
    project_service = services["project_service"]
    site_service = services["site_service"]
    site_a = site_service.create_site(site_code="SITE-N1", name="Name Filter Site")

    hamburg = project_service.create_project(
        "Hamburg Refit", client_name="Northwind Shipping", site_id=site_a.id
    )
    project_service.create_project("Hamburg Overhaul", client_name="Contoso Freight")
    project_service.create_project("Rotterdam Refit", client_name="Northwind Shipping")

    # Project name alone narrows to both "Hamburg" projects regardless of client.
    by_name = project_service.query_catalog_page(project_name="hamburg", page=1, page_size=25)
    assert by_name.filtered_total == 2
    assert all("hamburg" in row.project.name.lower() for row in by_name.items)

    # Client name alone narrows to both Northwind projects regardless of site/name.
    by_client = project_service.query_catalog_page(client_name="northwind", page=1, page_size=25)
    assert by_client.filtered_total == 2
    assert all((row.project.client_name or "").lower() == "northwind shipping" for row in by_client.items)

    # Composed AND: only the single project matching both narrows to it.
    composed = project_service.query_catalog_page(
        project_name="hamburg", client_name="northwind", page=1, page_size=25
    )
    assert composed.filtered_total == 1
    assert composed.items[0].project.id == hamburg.id

    # No match anywhere -> zero results, not an error.
    no_match = project_service.query_catalog_page(project_name="nonexistent-xyz", page=1, page_size=25)
    assert no_match.filtered_total == 0


def test_project_department_id_round_trips_through_create_and_update(services) -> None:
    project_service = services["project_service"]
    department_service = services["department_service"]

    dept_a = department_service.create_department(department_code="DEPT-RT-A", name="Engineering")
    dept_b = department_service.create_department(department_code="DEPT-RT-B", name="Operations")

    created = project_service.create_project("Round Trip Project", department_id=dept_a.id)
    assert created.department_id == dept_a.id
    fetched = project_service.get_project(created.id)
    assert fetched.department_id == dept_a.id

    updated = project_service.update_project(
        created.id,
        expected_version=fetched.version,
        department_id=dept_b.id,
    )
    assert updated.department_id == dept_b.id
    refetched = project_service.get_project(created.id)
    assert refetched.department_id == dept_b.id


def test_project_update_records_actor_and_field_level_activity_diff(services) -> None:
    """Real DB proof for the ProjectLifecycleMixin diff-tracking fix: the
    recorded activity entry must carry both who made the change (actor_id,
    resolved from the authenticated principal) and a before/after diff for
    every field that actually changed -- not just the final snapshot."""
    project_service = services["project_service"]
    department_service = services["department_service"]
    activity_service = services["activity_service"]
    actor_id = services["user_session"].principal.user_id

    dept_a = department_service.create_department(department_code="DEPT-ACT-A", name="Engineering")
    dept_b = department_service.create_department(department_code="DEPT-ACT-B", name="Operations")

    created = project_service.create_project(
        "Activity Diff Project", department_id=dept_a.id, status=ProjectStatus.PLANNED
    )

    project_service.update_project(
        created.id,
        expected_version=created.version,
        name="Activity Diff Project Renamed",
        status=ProjectStatus.ACTIVE,
        department_id=dept_b.id,
    )

    entries = activity_service.list_recent(entity_type="project", entity_id=created.id)
    update_entry = next(e for e in entries if e.action == "project.update")

    assert update_entry.actor_id == actor_id
    changes = update_entry.details["changes"]
    assert changes["name"] == {"from": "Activity Diff Project", "to": "Activity Diff Project Renamed"}
    assert changes["status"] == {"from": "PLANNED", "to": "ACTIVE"}
    assert changes["department_id"] == {"from": dept_a.id, "to": dept_b.id}
    # Unchanged fields (e.g. description) must not appear in the diff.
    assert "description" not in changes


def test_project_set_status_records_before_and_after_status(services) -> None:
    project_service = services["project_service"]
    activity_service = services["activity_service"]

    created = project_service.create_project("Status Diff Project", status=ProjectStatus.PLANNED)
    project_service.set_status(created.id, ProjectStatus.ON_HOLD)

    entries = activity_service.list_recent(entity_type="project", entity_id=created.id)
    status_entry = next(e for e in entries if e.action == "project.set_status")

    assert status_entry.details["changes"]["status"] == {"from": "PLANNED", "to": "ON_HOLD"}


def test_project_catalog_sort_is_authoritative_across_pages(services) -> None:
    project_service = services["project_service"]
    alpha = project_service.create_project("Alpha Sort")
    beta = project_service.create_project("Beta Sort")
    gamma = project_service.create_project("Gamma Sort")

    ascending_first = project_service.query_catalog_page(
        sort_key="title", sort_direction="asc", page=1, page_size=2
    )
    ascending_second = project_service.query_catalog_page(
        sort_key="title", sort_direction="asc", page=2, page_size=2
    )
    descending_first = project_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=1, page_size=2
    )
    descending_second = project_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=2, page_size=2
    )
    unsupported = project_service.query_catalog_page(
        sort_key="arbitrary_sql", sort_direction="desc", page=1, page_size=3
    )
    beyond_last = project_service.query_catalog_page(
        sort_key="title", sort_direction="asc", page=99, page_size=2
    )

    assert [row.project.id for row in ascending_first.items] == [alpha.id, beta.id]
    assert [row.project.id for row in ascending_second.items] == [gamma.id]
    assert [row.project.id for row in descending_first.items] == [gamma.id, beta.id]
    assert [row.project.id for row in descending_second.items] == [alpha.id]
    assert descending_first.sort.key == "title"
    assert descending_first.sort.direction.value == "desc"
    assert [row.project.id for row in unsupported.items] == [alpha.id, beta.id, gamma.id]
    assert unsupported.sort.key == "title"
    assert unsupported.sort.direction.value == "asc"
    assert beyond_last.page == 2
    assert [row.project.id for row in beyond_last.items] == [gamma.id]


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


def test_task_workspace_milestones_only_filter(services) -> None:
    project_service = services["project_service"]
    task_service = services["task_service"]
    project = project_service.create_project("Milestone Filter Project")
    task_service.create_task(
        project.id, "Regular Task", start_date=date(2026, 5, 1), duration_days=5
    )
    milestone = task_service.create_task(
        project.id, "Handover", start_date=date(2026, 5, 5), duration_days=5, is_milestone=True
    )

    all_page = task_service.query_workspace_page(project_id=project.id, page=1, page_size=25)
    milestones_page = task_service.query_workspace_page(
        project_id=project.id, milestones_only=True, page=1, page_size=25
    )

    assert all_page.filtered_total == 2
    assert milestones_page.filtered_total == 1
    assert [item.id for item in milestones_page.items] == [milestone.id]
    assert milestones_page.items[0].is_milestone is True
    assert milestones_page.items[0].duration_days == 0


def test_task_workspace_sort_is_authoritative_across_pages(services) -> None:
    project = services["project_service"].create_project("Task Sort Project")
    task_service = services["task_service"]
    alpha = task_service.create_task(project.id, "Alpha Task", wbs_code="1")
    beta = task_service.create_task(project.id, "Beta Task", wbs_code="2")
    gamma = task_service.create_task(project.id, "Gamma Task", wbs_code="3")

    ascending_first = task_service.query_workspace_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="asc",
        page=1,
        page_size=2,
    )
    ascending_second = task_service.query_workspace_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="asc",
        page=2,
        page_size=2,
    )
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
    beyond_last = task_service.query_workspace_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="asc",
        page=99,
        page_size=2,
    )

    assert [row.id for row in ascending_first.items] == [alpha.id, beta.id]
    assert [row.id for row in ascending_second.items] == [gamma.id]
    assert [row.id for row in first.items] == [gamma.id, beta.id]
    assert [row.id for row in second.items] == [alpha.id]
    assert first.sort.direction.value == "desc"
    assert [row.id for row in unsupported.items] == [alpha.id, beta.id, gamma.id]
    assert unsupported.sort.key == "wbsCode"
    assert unsupported.sort.direction.value == "asc"
    assert beyond_last.page == 2
    assert [row.id for row in beyond_last.items] == [gamma.id]


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
        search_text="planner",
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
    assert first_page.items[0].resource_id == employee_resource.id
    assert second_page.items[0].resource_id == vendor_resource.id
    assert employee_search.items[0].department_label == "Delivery"
    assert inactive_equipment.filtered_total == 1
    assert inactive_equipment.items[0].resource_id == vendor_resource.id


def test_resource_catalog_sort_is_authoritative_across_pages(services) -> None:
    resource_service = services["resource_service"]
    alpha = resource_service.create_resource(name="Alpha Resource", role="Planner")
    beta = resource_service.create_resource(name="Beta Resource", role="Planner")
    gamma = resource_service.create_resource(name="Gamma Resource", role="Planner")

    ascending_first = resource_service.query_catalog_page(
        sort_key="title", sort_direction="asc", page=1, page_size=2
    )
    ascending_second = resource_service.query_catalog_page(
        sort_key="title", sort_direction="asc", page=2, page_size=2
    )
    first = resource_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=1, page_size=2
    )
    second = resource_service.query_catalog_page(
        sort_key="title", sort_direction="desc", page=2, page_size=2
    )
    unsupported = resource_service.query_catalog_page(
        sort_key="unsafe_sql", sort_direction="desc", page=1, page_size=3
    )
    beyond_last = resource_service.query_catalog_page(
        sort_key="title", sort_direction="asc", page=99, page_size=2
    )

    assert [row.resource_id for row in ascending_first.items] == [alpha.id, beta.id]
    assert [row.resource_id for row in ascending_second.items] == [gamma.id]
    assert [row.resource_id for row in first.items] == [gamma.id, beta.id]
    assert [row.resource_id for row in second.items] == [alpha.id]
    assert first.sort.direction.value == "desc"
    assert [row.resource_id for row in unsupported.items] == [alpha.id, beta.id, gamma.id]
    assert unsupported.sort.key == "catalog"
    assert unsupported.sort.direction.value == "asc"
    assert beyond_last.page == 2
    assert [row.resource_id for row in beyond_last.items] == [gamma.id]


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

    ascending_first = register_service.query_catalog_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="asc",
        page=1,
        page_size=2,
    )
    ascending_second = register_service.query_catalog_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="asc",
        page=2,
        page_size=2,
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
    beyond_last = register_service.query_catalog_page(
        project_id=project.id,
        sort_key="title",
        sort_direction="asc",
        page=99,
        page_size=2,
    )

    assert [row.entry.id for row in ascending_first.items] == [alpha.id, beta.id]
    assert [row.entry.id for row in ascending_second.items] == [gamma.id]
    assert [row.entry.id for row in first.items] == [gamma.id, beta.id]
    assert [row.entry.id for row in second.items] == [alpha.id]
    assert first.sort.direction.value == "desc"
    assert unsupported.sort.key == "triage"
    assert unsupported.sort.direction.value == "asc"
    assert beyond_last.page == 2
    assert [row.entry.id for row in beyond_last.items] == [gamma.id]


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


def test_timesheet_review_query_filters_and_sorts_across_pages(services) -> None:
    project_service = services["project_service"]
    task_service = services["task_service"]
    resource_service = services["resource_service"]
    timesheets = services["timesheet_service"]
    alpha_project = project_service.create_project("Alpha Review Project")
    beta_project = project_service.create_project("Beta Review Project")

    created = []
    for name, project, month in (
        ("Aaron Reviewer", alpha_project, 6),
        ("Maya Reviewer", alpha_project, 7),
        ("Zoe Reviewer", beta_project, 8),
    ):
        task = task_service.create_task(project.id, f"{name} Task")
        resource = resource_service.create_resource(name=name, role="Engineer")
        assignment = task_service.assign_resource(task.id, resource.id)
        period_start = date(2026, month, 1)
        timesheets.add_time_entry(
            assignment.id,
            entry_date=date(2026, month, 2),
            hours=8,
            note=f"{name} database review",
        )
        period = timesheets.submit_timesheet_period(
            resource.id,
            period_start=period_start,
        )
        created.append((resource, period))

    ascending_first = timesheets.query_review_queue_page(
        sort_key="title", sort_direction="asc", page=1, page_size=2
    )
    ascending_second = timesheets.query_review_queue_page(
        sort_key="title", sort_direction="asc", page=2, page_size=2
    )
    first = timesheets.query_review_queue_page(
        sort_key="title", sort_direction="desc", page=1, page_size=2
    )
    second = timesheets.query_review_queue_page(
        sort_key="title", sort_direction="desc", page=2, page_size=2
    )
    project_page = timesheets.query_review_queue_page(project_id=alpha_project.id)
    resource_page = timesheets.query_review_queue_page(resource_id=created[1][0].id)
    date_page = timesheets.query_review_queue_page(
        period_start_from=date(2026, 7, 1),
        period_start_to=date(2026, 7, 31),
    )
    search_page = timesheets.query_review_queue_page(search_text="Zoe Reviewer")
    unsupported = timesheets.query_review_queue_page(
        sort_key="unsafe_sql", sort_direction="asc"
    )
    beyond_last = timesheets.query_review_queue_page(
        sort_key="title", sort_direction="asc", page=99, page_size=2
    )

    assert [row.resource_name for row in ascending_first.items] == [
        "Aaron Reviewer",
        "Maya Reviewer",
    ]
    assert [row.resource_name for row in ascending_second.items] == ["Zoe Reviewer"]
    assert [row.resource_name for row in first.items] == ["Zoe Reviewer", "Maya Reviewer"]
    assert [row.resource_name for row in second.items] == ["Aaron Reviewer"]
    assert {row.resource_name for row in project_page.items} == {
        "Aaron Reviewer",
        "Maya Reviewer",
    }
    assert [row.resource_name for row in resource_page.items] == ["Maya Reviewer"]
    assert [row.resource_name for row in date_page.items] == ["Maya Reviewer"]
    assert [row.resource_name for row in search_page.items] == ["Zoe Reviewer"]
    assert unsupported.sort.key == "submittedAt"
    assert unsupported.sort.direction.value == "desc"
    assert beyond_last.page == 2
    assert [row.resource_name for row in beyond_last.items] == ["Zoe Reviewer"]


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
