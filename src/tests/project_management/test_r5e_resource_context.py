from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent
from PySide6.QtQuick import QQuickItem
from sqlalchemy import event

from src.core.modules.project_management.contracts.reads import ReadSort
from src.core.modules.project_management.api.desktop.resources.commands.skill_commands import (
    ResourceAddSkillCommand,
)
from src.core.modules.project_management.api.desktop.resources.factories.resources_api_factory import (
    build_project_management_resources_desktop_api,
)
from src.core.modules.project_management.domain.enums import ProjectStatus, TaskStatus
from src.core.platform.domain.security.auth.session import UserSessionPrincipal
from src.ui_qml.modules.project_management.controllers.resources.resource_context_handler import (
    load_resource_activity,
)
from src.ui_qml.modules.project_management.controllers.resources import (
    resource_domain_event_binder,
)
from src.ui_qml.shell.qml_engine import create_qml_engine


def _seed_resource_context(services):
    project_service = services["project_service"]
    task_service = services["task_service"]
    resource_service = services["resource_service"]
    project_resource_service = services["project_resource_service"]

    resource = resource_service.create_resource("R5E Planner", role="Planner")
    alpha = project_service.create_project(
        "Alpha Delivery",
        code="R5E-ALPHA",
        status=ProjectStatus.ACTIVE,
        start_date=date(2026, 8, 1),
        end_date=date(2026, 12, 31),
    )
    zulu = project_service.create_project(
        "Zulu Delivery",
        code="R5E-ZULU",
        status=ProjectStatus.PLANNED,
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 31),
    )
    alpha_resource = project_resource_service.add_to_project(
        alpha.id, resource.id, planned_hours=Decimal("120")
    )
    zulu_resource = project_resource_service.add_to_project(
        zulu.id, resource.id, planned_hours=Decimal("80")
    )
    alpha_task = task_service.create_task(
        alpha.id,
        "Alpha planning",
        code="R5E-A-TASK",
        start_date=date(2026, 8, 10),
        duration_days=4,
        status=TaskStatus.IN_PROGRESS,
    )
    zulu_task = task_service.create_task(
        zulu.id,
        "Zulu planning",
        code="R5E-Z-TASK",
        start_date=date(2026, 9, 10),
        duration_days=4,
    )
    alpha_assignment = task_service.assign_project_resource(
        alpha_task.id,
        alpha_resource.id,
        allocation_percent=50,
        allocated_planned_hours=Decimal("40"),
    )
    zulu_assignment = task_service.assign_project_resource(
        zulu_task.id,
        zulu_resource.id,
        allocation_percent=25,
        allocated_planned_hours=Decimal("30"),
    )
    task_service.add_time_entry(
        alpha_assignment.id,
        entry_date=date(2026, 8, 12),
        hours=25,
        note="Alpha actual work",
    )
    task_service.add_time_entry(
        zulu_assignment.id,
        entry_date=date(2026, 9, 12),
        hours=10,
        note="Zulu actual work",
    )
    return SimpleNamespace(
        resource=resource,
        alpha=alpha,
        zulu=zulu,
        alpha_resource=alpha_resource,
        zulu_resource=zulu_resource,
        alpha_task=alpha_task,
        zulu_task=zulu_task,
        alpha_assignment=alpha_assignment,
        zulu_assignment=zulu_assignment,
    )


def _count_statements(session, operation):
    statements: list[str] = []

    def capture(_conn, _cursor, statement, _parameters, _context, _many) -> None:
        statements.append(str(statement))

    engine = session.get_bind()
    event.listen(engine, "before_cursor_execute", capture)
    try:
        result = operation()
    finally:
        event.remove(engine, "before_cursor_execute", capture)
    return result, statements


def test_r5e_projects_are_immutable_server_paged_sorted_and_bounded(services) -> None:
    seeded = _seed_resource_context(services)
    resource_service = services["resource_service"]
    session = services["project_service"]._session

    ascending, statements = _count_statements(
        session,
        lambda: resource_service.query_resource_projects_page(
            seeded.resource.id,
            page=1,
            page_size=1,
            sort_key="projectName",
            sort_direction="asc",
        ),
    )
    descending = resource_service.query_resource_projects_page(
        seeded.resource.id,
        page=1,
        page_size=1,
        sort_key="projectName",
        sort_direction="desc",
    )

    assert ascending.filtered_total == 2
    assert len(ascending.items) == 1
    assert ascending.items[0].project_name == "Alpha Delivery"
    assert descending.items[0].project_name == "Zulu Delivery"
    assert len(statements) <= 3
    with pytest.raises(FrozenInstanceError):
        ascending.items[0].project_name = "Mutated"  # type: ignore[misc]


def test_r5e_assignments_keep_project_envelope_planned_and_actual_distinct(services) -> None:
    seeded = _seed_resource_context(services)
    resource_service = services["resource_service"]
    session = services["project_service"]._session

    page, statements = _count_statements(
        session,
        lambda: resource_service.query_resource_assignments_page(
            seeded.resource.id,
            lifecycle="all",
            page=1,
            page_size=25,
            sort_key="actualHours",
            sort_direction="desc",
        ),
    )
    by_task = {item.task_id: item for item in page.items}

    assert page.filtered_total == 2
    assert len(statements) <= 3
    assert by_task[seeded.alpha_task.id].allocated_planned_hours == Decimal("40")
    assert by_task[seeded.zulu_task.id].allocated_planned_hours == Decimal("30")
    assert by_task[seeded.alpha_task.id].actual_hours == Decimal("25")
    assert by_task[seeded.zulu_task.id].actual_hours == Decimal("10")
    assert {item.actual_hours_source for item in page.items} == {"time_entries"}
    assert seeded.alpha_resource.planned_hours == Decimal("120")
    assert sum(item.allocated_planned_hours for item in page.items) == Decimal("70")
    assert sum(item.actual_hours for item in page.items) == Decimal("35")


def test_r5e_assignment_filters_and_cross_page_sort_are_authoritative(services) -> None:
    seeded = _seed_resource_context(services)
    resource_service = services["resource_service"]

    first = resource_service.query_resource_assignments_page(
        seeded.resource.id,
        lifecycle="all",
        page=1,
        page_size=1,
        sort_key="taskName",
        sort_direction="asc",
    )
    second = resource_service.query_resource_assignments_page(
        seeded.resource.id,
        lifecycle="all",
        page=2,
        page_size=1,
        sort_key="taskName",
        sort_direction="asc",
    )
    september = resource_service.query_resource_assignments_page(
        seeded.resource.id,
        lifecycle="all",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 9, 30),
    )

    assert [first.items[0].task_name, second.items[0].task_name] == [
        "Alpha planning",
        "Zulu planning",
    ]
    assert [item.task_id for item in september.items] == [seeded.zulu_task.id]


def test_r5e_project_scope_hides_project_assignment_and_activity_identity(services) -> None:
    seeded = _seed_resource_context(services)
    resource_service = services["resource_service"]
    user_session = services["user_session"]
    original = user_session.principal
    assert original is not None
    user_session.set_principal(
        UserSessionPrincipal(
            user_id=original.user_id,
            username=original.username,
            display_name=original.display_name,
            role_names=frozenset(),
            permissions=original.permissions,
            scoped_access={
                "project": {
                    seeded.alpha.id: frozenset({"project.read", "task.read"})
                }
            },
            active_tenant_id=original.active_tenant_id,
            active_organization_id=original.active_organization_id,
        )
    )
    try:
        projects = resource_service.query_resource_projects_page(seeded.resource.id)
        assignments = resource_service.query_resource_assignments_page(
            seeded.resource.id, lifecycle="all"
        )
        activity = resource_service.query_resource_activity_page(
            seeded.resource.id, category="all", page_size=100
        )
    finally:
        user_session.set_principal(original)

    assert {item.project_id for item in projects.items} == {seeded.alpha.id}
    assert {item.project_id for item in assignments.items} == {seeded.alpha.id}
    assert seeded.zulu.id not in {item.project_id for item in activity.items}
    assert seeded.zulu_task.id not in {item.task_id for item in activity.items}


def test_r5e_readers_fail_closed_for_wrong_tenant_and_organization(services) -> None:
    seeded = _seed_resource_context(services)
    resource_service = services["resource_service"]
    reader = resource_service._resource_projects_reader
    tenant_id = services["user_session"].stored_active_tenant_id()
    organization_id = services["user_session"].stored_active_organization_id()

    wrong_tenant = reader.read_projects_page(
        tenant_id="other-tenant",
        organization_id=organization_id,
        resource_id=seeded.resource.id,
        allowed_project_ids=None,
        search_text="",
        active=None,
        status=None,
        page=1,
        page_size=25,
        sort=ReadSort("projectName"),
    )
    wrong_organization = reader.read_projects_page(
        tenant_id=tenant_id,
        organization_id="other-organization",
        resource_id=seeded.resource.id,
        allowed_project_ids=None,
        search_text="",
        active=None,
        status=None,
        page=1,
        page_size=25,
        sort=ReadSort("projectName"),
    )

    assert wrong_tenant.filtered_total == 0
    assert wrong_organization.filtered_total == 0


def test_r5e_activity_uses_authoritative_ledger_categories_order_and_paging(services) -> None:
    seeded = _seed_resource_context(services)
    resource_service = services["resource_service"]
    desktop_api = build_project_management_resources_desktop_api(
        resource_service=resource_service
    )
    desktop_api.add_resource_skill(
        ResourceAddSkillCommand(
            resource_id=seeded.resource.id,
            skill_code="R5E-PLAN",
            skill_name="Planning",
        )
    )
    session = services["project_service"]._session

    page, statements = _count_statements(
        session,
        lambda: resource_service.query_resource_activity_page(
            seeded.resource.id, page=1, page_size=100
        ),
    )
    event_types = {item.event_type for item in page.items}

    assert len(statements) <= 3
    assert "resource.created" in event_types
    assert "resource.skill.added" in event_types
    assert "project_resource.add" in event_types
    assert "assignment.add" in event_types
    assert [item.occurred_at for item in page.items] == sorted(
        (item.occurred_at for item in page.items), reverse=True
    )
    assert resource_service.query_resource_activity_page(
        seeded.resource.id, category="projects", page_size=100
    ).items
    assert resource_service.query_resource_activity_page(
        seeded.resource.id, category="assignments", page_size=100
    ).items
    assert len(
        resource_service.query_resource_activity_page(
            seeded.resource.id, page=1, page_size=1
        ).items
    ) == 1


def test_r5e_activity_failure_is_section_error_not_empty_history() -> None:
    errors: dict[str, str] = {}
    old_page = {"items": [{"id": "existing"}], "total": 1}
    controller = SimpleNamespace(
        _selected_resource_id="resource-1",
        _resource_activity=old_page,
        _resource_activity_loaded_for=None,
        _resource_activity_request_id=0,
        _resource_activity_loading=False,
        _resource_activity_category="all",
        _resource_activity_start_date="",
        _resource_activity_end_date="",
        _resource_activity_page=1,
        _resource_activity_page_size=25,
        resourceActivityLoadingChanged=SimpleNamespace(emit=lambda: None),
        _clear_section_error=lambda section: errors.pop(section, None),
        _set_section_error=lambda section, message: errors.__setitem__(section, message),
        _resources_workspace_presenter=SimpleNamespace(
            build_resource_activity_page=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                RuntimeError("activity query failed")
            )
        ),
    )

    load_resource_activity(controller, force=True)

    assert controller._resource_activity is old_page
    assert errors["activity"] == "activity query failed"


def test_r5e_late_activity_response_cannot_replace_new_resource() -> None:
    changed = []
    controller = SimpleNamespace(
        _selected_resource_id="resource-a",
        _resource_activity={"items": [{"id": "resource-b-existing"}]},
        _resource_activity_loaded_for=None,
        _resource_activity_request_id=0,
        _resource_activity_loading=False,
        _resource_activity_category="all",
        _resource_activity_start_date="",
        _resource_activity_end_date="",
        _resource_activity_page=1,
        _resource_activity_page_size=25,
        resourceActivityLoadingChanged=SimpleNamespace(emit=lambda: None),
        resourceActivityChanged=SimpleNamespace(emit=lambda: changed.append(True)),
        _clear_section_error=lambda _section: None,
        _set_section_error=lambda _section, _message: None,
    )

    def late_page(*_args, **_kwargs):
        controller._selected_resource_id = "resource-b"
        controller._resource_activity_request_id += 1
        return {"items": [{"id": "resource-a-late"}], "total": 1}

    controller._resources_workspace_presenter = SimpleNamespace(
        build_resource_activity_page=late_page
    )
    load_resource_activity(controller, force=True)

    assert controller._resource_activity == {"items": [{"id": "resource-b-existing"}]}
    assert changed == []


def test_r5e_targeted_invalidation_reloads_only_loaded_context(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    controller = SimpleNamespace(
        _selected_resource_id="resource-1",
        _resource_projects_loaded_for="resource-1",
        _resource_assignments_loaded_for="resource-1",
        _resource_activity_loaded_for="resource-1",
        _resource_availability={
            "resourceId": "resource-1",
            "startDate": "2026-08-01",
            "endDate": "2026-08-31",
        },
    )
    monkeypatch.setattr(
        resource_domain_event_binder,
        "load_resource_projects",
        lambda _controller, force=False: calls.append(("projects", force)),
    )
    monkeypatch.setattr(
        resource_domain_event_binder,
        "load_resource_assignments",
        lambda _controller, force=False: calls.append(("assignments", force)),
    )
    monkeypatch.setattr(
        resource_domain_event_binder,
        "load_resource_activity",
        lambda _controller, force=False: calls.append(("activity", force)),
    )
    monkeypatch.setattr(
        resource_domain_event_binder,
        "load_resource_availability",
        lambda _controller, start, end: calls.append(("availability", (start, end))),
    )

    resource_domain_event_binder._reload_if_loaded(controller, "assignments")
    resource_domain_event_binder._reload_availability_if_loaded(controller)
    resource_domain_event_binder._reload_if_loaded(controller, "activity")

    assert calls == [
        ("assignments", True),
        ("availability", ("2026-08-01", "2026-08-31")),
        ("activity", True),
    ]
    assert not any(name == "projects" for name, _value in calls)


def test_r5e_qml_uses_canonical_navigation_shared_activity_and_read_only_sections() -> None:
    root = Path("src/ui_qml/modules/project_management/qml/workspaces/resources/sections")
    projects = (root / "ResourcesProjectsSection.qml").read_text(encoding="utf-8")
    assignments = (root / "ResourcesAssignmentsSection.qml").read_text(encoding="utf-8")
    activity = (root / "ResourcesActivitySection.qml").read_text(encoding="utf-8")
    task_state = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksWorkspaceState.qml"
    ).read_text(encoding="utf-8")

    assert 'sortingMode: "server"' in projects
    assert 'sortingMode: "server"' in assignments
    assert 'openEntity("projects", projectId, "overview")' in projects
    assert 'openEntity("tasks", taskId, "details")' in assignments
    assert "PMWidgets.ActivityLogSection" in activity
    assert "clientSideSearch: false" in activity
    assert "createAssignment" not in assignments
    assert "deleteAssignment" not in assignments
    assert '"Details", "Assignments", "Skills", "Dependencies", "Time"' in task_state
    assert not (root / "ResourcesDeferredSection.qml").exists()


@pytest.mark.parametrize(
    ("width", "height"),
    [(1024, 640), (1280, 720), (1366, 768), (1440, 900), (1920, 1080)],
)
@pytest.mark.parametrize(
    ("filename", "pagination_name"),
    [
        ("ResourcesProjectsSection.qml", "resourceProjectsPagination"),
        ("ResourcesAssignmentsSection.qml", "resourceAssignmentsPagination"),
        ("ResourcesActivitySection.qml", "resourceActivityPagination"),
    ],
)
def test_r5e_sections_pin_pagination_to_available_bottom(
    qapp, width: int, height: int, filename: str, pagination_name: str
) -> None:
    engine = create_qml_engine()
    source = Path(
        "src/ui_qml/modules/project_management/qml/workspaces/resources/sections"
    ).resolve() / filename
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(source)))
    section = component.create()
    assert section is not None, "\n".join(error.toString() for error in component.errors())
    assert section.setProperty("width", width)
    assert section.setProperty("height", height)
    assert section.setProperty("availableHeight", height)
    qapp.processEvents()

    pagination = section.findChild(QQuickItem, pagination_name)
    assert pagination is not None
    bottom = pagination.height()
    current = pagination
    while current is not section:
        bottom += current.y()
        current = current.parentItem()
        assert current is not None
    assert abs(bottom - height) <= 1.0
