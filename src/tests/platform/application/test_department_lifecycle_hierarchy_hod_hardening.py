"""Department hardening (per the explicit user decision after the Site
closeout audit): a real 2-state (Active/Inactive, no Archive) lifecycle with
distinct guarded commands instead of the generic update_department(is_active=
...) path; transitive parent-department cycle detection, not just direct
self-parenting; and Head of Department (HOD) fully wired from the dialog
through the presenter's create/update payload mapping and read-model name
resolution."""

from __future__ import annotations

import pytest

from src.application.runtime import build_desktop_api_registry
from src.core.platform.application.master_data.department.dto import (
    DepartmentCreateCommand,
    DepartmentUpdateCommand,
)
from src.core.platform.application.master_data.employee.dto import (
    EmployeeCreateCommand,
)
from src.core.platform.common.exceptions import ValidationError
from src.ui_qml.platform.context import PlatformWorkspaceCatalog

# --------------------------------------------------------------------------
# Lifecycle: explicit activate_department/deactivate_department
# --------------------------------------------------------------------------


def test_create_department_always_starts_active(services) -> None:
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-CREATE", name="Lifecycle Create"))
    assert created.is_active is True


def test_create_department_no_longer_accepts_is_active_kwarg(services) -> None:
    with pytest.raises(TypeError):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-NOARG", name="X", is_active=False))


def test_update_department_no_longer_accepts_is_active_kwarg(services) -> None:
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-NOARG-U", name="X"))
    with pytest.raises(TypeError):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=created.id, is_active=False))


def test_activate_and_deactivate_department_are_explicit_commands(services) -> None:
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-TOGGLE", name="Toggle Dept"))
    assert created.is_active is True

    deactivated = services["department_commands"].deactivate_department(created.id)
    assert deactivated.is_active is False

    activated = services["department_commands"].activate_department(created.id)
    assert activated.is_active is True


def test_deactivating_an_already_inactive_department_is_rejected(services) -> None:
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-GUARD-1", name="Guard Dept"))
    services["department_commands"].deactivate_department(created.id)

    with pytest.raises(ValidationError) as exc_info:
        services["department_commands"].deactivate_department(created.id)
    assert exc_info.value.code == "DEPARTMENT_ALREADY_INACTIVE"


def test_activating_an_already_active_department_is_rejected(services) -> None:
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-GUARD-2", name="Guard Dept Two"))

    with pytest.raises(ValidationError) as exc_info:
        services["department_commands"].activate_department(created.id)
    assert exc_info.value.code == "DEPARTMENT_ALREADY_ACTIVE"


def test_deactivate_department_records_distinct_activity_action(services) -> None:
    activity_service = services["activity_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-ACT-1", name="Activity Dept"))
    services["department_commands"].deactivate_department(created.id)

    entries = activity_service.list_recent_for_entity("department", created.id, organization_id)
    actions = [entry.action for entry in entries]
    assert "department.deactivate" in actions
    assert "department.update" not in actions  # never the generic fallback for a lifecycle change

    deactivate_entry = next(entry for entry in entries if entry.action == "department.deactivate")
    assert "deactivated" in deactivate_entry.human_message.lower()


def test_activate_department_records_distinct_activity_action(services) -> None:
    activity_service = services["activity_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-ACT-2", name="Activity Dept Two"))
    services["department_commands"].deactivate_department(created.id)
    services["department_commands"].activate_department(created.id)

    entries = activity_service.list_recent_for_entity("department", created.id, organization_id)
    actions = [entry.action for entry in entries]
    assert "department.activate" in actions

    activate_entry = next(entry for entry in entries if entry.action == "department.activate")
    assert "activated" in activate_entry.human_message.lower()


def test_deactivating_a_department_does_not_delete_or_cascade_to_employees(services) -> None:

    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-CASCADE", name="Cascade Dept"))
    employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="LC-CASCADE-E1", full_name="Cascade Employee", department_id=created.id))
    services["department_commands"].deactivate_department(created.id)

    reloaded_department = services["department_query"].get_department(created.id)
    assert reloaded_department is not None
    assert reloaded_department.is_active is False

    reloaded_employee = services["employee_query"].get_employee(employee.id)
    assert reloaded_employee is not None
    assert reloaded_employee.department_id == created.id


def test_inactive_department_remains_readable_in_full_listing(services) -> None:
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="LC-READABLE", name="Readable Dept"))
    services["department_commands"].deactivate_department(created.id)

    names = [d.name for d in services["department_query"].list_departments(active_only=None)]
    assert "Readable Dept" in names


# --------------------------------------------------------------------------
# Multi-level (transitive) parent-department cycle detection
# --------------------------------------------------------------------------


def test_department_with_no_parent_is_valid(services) -> None:
    created = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-NONE", name="No Parent Dept"))
    assert created.parent_department_id is None


def test_department_with_a_valid_parent_is_accepted(services) -> None:
    parent = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-PARENT", name="Parent Dept"))
    child = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-CHILD", name="Child Dept", parent_department_id=parent.id))
    assert child.parent_department_id == parent.id


def test_direct_self_parent_is_still_rejected(services) -> None:
    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-SELF", name="Self Dept"))
    with pytest.raises(ValidationError, match="cannot be its own parent"):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, parent_department_id=department.id, expected_version=department.version))


def test_two_node_cycle_is_rejected(services) -> None:
    """A -> B, then attempting B -> A."""
    a = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-2A", name="A"))
    b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-2B", name="B", parent_department_id=a.id))

    with pytest.raises(ValidationError, match="cycle") as exc_info:
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=a.id, parent_department_id=b.id, expected_version=a.version))
    assert exc_info.value.code == "DEPARTMENT_PARENT_CYCLE"


def test_three_level_cycle_is_rejected(services) -> None:
    """Chain: leaf.parent = mid, mid.parent = root (leaf -> mid -> root).
    Attempting to then set root's own parent to leaf would close the loop
    (root -> leaf -> mid -> root) -- rejected even though it's the ROOT
    being re-parented to a distant descendant, not a direct self-parent."""
    root = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-3-ROOT", name="Root3"))
    mid = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-3-MID", name="Mid3", parent_department_id=root.id))
    leaf = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-3-LEAF", name="Leaf3", parent_department_id=mid.id))

    with pytest.raises(ValidationError, match="cycle") as exc_info:
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=root.id, parent_department_id=leaf.id, expected_version=root.version))
    assert exc_info.value.code == "DEPARTMENT_PARENT_CYCLE"


def test_deeper_cycle_is_rejected(services) -> None:
    """Chain: a (root, no parent) -> b -> c -> d -> e (each .parent points
    to the previous). Re-parenting b (not the true root a) to its own
    descendant e would close a b->c->d->e->b loop without touching a at
    all -- proving the walk checks the whole chain, not just the root."""
    a = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-DEEP-A", name="DA"))
    b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-DEEP-B", name="DB", parent_department_id=a.id))
    c = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-DEEP-C", name="DC", parent_department_id=b.id))
    d = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-DEEP-D", name="DD", parent_department_id=c.id))
    e = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-DEEP-E", name="DE", parent_department_id=d.id))

    with pytest.raises(ValidationError, match="cycle") as exc_info:
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=b.id, parent_department_id=e.id, expected_version=b.version))
    assert exc_info.value.code == "DEPARTMENT_PARENT_CYCLE"


def test_valid_deep_hierarchy_is_accepted(services) -> None:
    """A -> B -> C -> D, then re-pointing D at A is NOT a cycle (A has no
    parent), and must be accepted."""
    a = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-VALID-A", name="VA"))
    b = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-VALID-B", name="VB", parent_department_id=a.id))
    c = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-VALID-C", name="VC", parent_department_id=b.id))
    d = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-VALID-D", name="VD"))

    updated = services["department_commands"].update_department(DepartmentUpdateCommand(department_id=d.id, parent_department_id=c.id, expected_version=d.version))
    assert updated.parent_department_id == c.id


def test_cross_organization_parent_still_rejected_alongside_cycle_hardening(services) -> None:
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = services["organization_commands"].create_organization(
        organization_code="HIER-CROSSORG", display_name="Other Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_parent = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-FOREIGN", name="Foreign"))
    tenant_context_service.set_active_organization(default_organization.id)

    with pytest.raises(ValidationError, match="Parent department must belong to the active organization"):
        services["department_commands"].create_department(DepartmentCreateCommand(department_code="HIER-CROSSORG-CHILD", name="Child", parent_department_id=foreign_parent.id))


# --------------------------------------------------------------------------
# Head of Department (HOD): presenter payload mapping + read-model name
# resolution
# --------------------------------------------------------------------------


def test_create_department_rejects_head_of_department_because_no_employee_can_belong_yet(services) -> None:
    """A brand-new department has no id any employee could already
    reference -- Create intentionally never accepts an HOD; assignment is a
    post-creation Edit-only step once an employee is scoped to it."""
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    unrelated_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-OTHER-1", name="Other Dept"))
    candidate = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-1", full_name="Anna Mueller", department_id=unrelated_department.id))

    result = admin.createDepartment({
        "departmentCode": "HOD-DEPT-1",
        "name": "Department With HOD",
        "headOfDepartmentEmployeeId": candidate.id,
    })
    assert result["ok"] is False
    assert result["code"] == "DEPARTMENT_HEAD_OF_DEPARTMENT_WRONG_DEPARTMENT"


def test_update_department_head_of_department_accepts_employee_of_this_department(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-DEPT-2", name="Dept Two"))
    head_of_department = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-2", full_name="John Doe", department_id=department.id))

    result = admin.updateDepartment({
        "departmentId": department.id,
        "departmentCode": department.department_code,
        "name": department.name,
        "headOfDepartmentEmployeeId": head_of_department.id,
        "expectedVersion": department.version,
    })
    assert result["ok"] is True

    reloaded = services["department_query"].get_department(department.id)
    assert reloaded.head_of_department_employee_id == head_of_department.id


def test_update_department_head_of_department_rejects_employee_of_another_department(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-DEPT-2B", name="Dept Two B"))
    other_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-DEPT-2C", name="Dept Two C"))
    outsider = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-2B", full_name="Jane Roe", department_id=other_department.id))

    result = admin.updateDepartment({
        "departmentId": department.id,
        "departmentCode": department.department_code,
        "name": department.name,
        "headOfDepartmentEmployeeId": outsider.id,
        "expectedVersion": department.version,
    })
    assert result["ok"] is False
    assert result["code"] == "DEPARTMENT_HEAD_OF_DEPARTMENT_WRONG_DEPARTMENT"


def test_update_department_head_of_department_rejects_inactive_employee(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-DEPT-2D", name="Dept Two D"))
    inactive_employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-2D", full_name="Retired Person", department_id=department.id))
    services["employee_commands"].deactivate_employee(inactive_employee.id)

    result = admin.updateDepartment({
        "departmentId": department.id,
        "departmentCode": department.department_code,
        "name": department.name,
        "headOfDepartmentEmployeeId": inactive_employee.id,
        "expectedVersion": department.version,
    })
    assert result["ok"] is False
    assert result["code"] == "DEPARTMENT_HEAD_OF_DEPARTMENT_INACTIVE"


def test_clear_department_head_of_department_via_presenter_payload(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-DEPT-3", name="Dept Three"))
    head_of_department = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-3", full_name="Clear Me", department_id=department.id))
    assign_result = admin.updateDepartment({
        "departmentId": department.id,
        "departmentCode": department.department_code,
        "name": department.name,
        "headOfDepartmentEmployeeId": head_of_department.id,
        "expectedVersion": department.version,
    })
    assert assign_result["ok"] is True
    department = services["department_query"].get_department(department.id)
    assert department.head_of_department_employee_id == head_of_department.id

    result = admin.updateDepartment({
        "departmentId": department.id,
        "departmentCode": department.department_code,
        "name": department.name,
        "headOfDepartmentEmployeeId": "",
        "expectedVersion": department.version,
    })
    assert result["ok"] is True

    reloaded = services["department_query"].get_department(department.id)
    assert reloaded.head_of_department_employee_id is None


def test_cross_organization_head_of_department_still_rejected(services) -> None:
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-CROSSORG-DEPT", name="Cross Org Dept"))

    other_organization = services["organization_commands"].create_organization(
        organization_code="HOD-CROSSORG", display_name="Other Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-FOREIGN-DEPT", name="Foreign Dept"))
    foreign_employee = services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-FOREIGN", full_name="Foreign Head of Department", department_id=foreign_department.id))
    tenant_context_service.set_active_organization(default_organization.id)

    with pytest.raises(ValidationError, match="Department Head of Department must reference an existing employee"):
        services["department_commands"].update_department(DepartmentUpdateCommand(department_id=department.id, head_of_department_employee_id=foreign_employee.id))


def test_department_editor_options_never_include_hod_candidates_without_a_department_context(services) -> None:
    """Create has no department id yet -- the cached, org-wide
    departmentEditorOptions must never surface HOD candidates (no employee
    could possibly belong to a not-yet-created department)."""
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-OPT-DEPT", name="Option Dept"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-OPT-1", full_name="Option Employee One", department_id=department.id))
    admin.refresh()

    assert admin.departmentEditorOptions["headOfDepartmentOptions"] == []


def test_head_of_department_options_for_department_are_scoped_to_that_department_only(services) -> None:
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-OPT-DEPT-2", name="Option Dept Two"))
    other_department = services["department_commands"].create_department(DepartmentCreateCommand(department_code="HOD-OPT-DEPT-3", name="Option Dept Three"))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-OPT-2", full_name="Option Employee Two", department_id=department.id))
    services["employee_commands"].create_employee(EmployeeCreateCommand(employee_code="HOD-OPT-3", full_name="Outsider Employee", department_id=other_department.id))

    options = admin.headOfDepartmentOptionsFor(department.id)["headOfDepartmentOptions"]
    labels = [option["label"] for option in options]
    assert "Option Employee Two" in labels
    assert "Outsider Employee" not in labels
    # Never a bare UUID standing in for a label.
    for option in options:
        assert option["label"] != option["value"]
