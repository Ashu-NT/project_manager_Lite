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
from src.core.platform.common.exceptions import ValidationError
from src.ui_qml.platform.context import PlatformWorkspaceCatalog


# --------------------------------------------------------------------------
# Lifecycle: explicit activate_department/deactivate_department
# --------------------------------------------------------------------------


def test_create_department_always_starts_active(services) -> None:
    department_service = services["department_service"]
    created = department_service.create_department(department_code="LC-CREATE", name="Lifecycle Create")
    assert created.is_active is True


def test_create_department_no_longer_accepts_is_active_kwarg(services) -> None:
    department_service = services["department_service"]
    with pytest.raises(TypeError):
        department_service.create_department(department_code="LC-NOARG", name="X", is_active=False)


def test_update_department_no_longer_accepts_is_active_kwarg(services) -> None:
    department_service = services["department_service"]
    created = department_service.create_department(department_code="LC-NOARG-U", name="X")
    with pytest.raises(TypeError):
        department_service.update_department(created.id, is_active=False)


def test_activate_and_deactivate_department_are_explicit_commands(services) -> None:
    department_service = services["department_service"]
    created = department_service.create_department(department_code="LC-TOGGLE", name="Toggle Dept")
    assert created.is_active is True

    deactivated = department_service.deactivate_department(created.id)
    assert deactivated.is_active is False

    activated = department_service.activate_department(created.id)
    assert activated.is_active is True


def test_deactivating_an_already_inactive_department_is_rejected(services) -> None:
    department_service = services["department_service"]
    created = department_service.create_department(department_code="LC-GUARD-1", name="Guard Dept")
    department_service.deactivate_department(created.id)

    with pytest.raises(ValidationError) as exc_info:
        department_service.deactivate_department(created.id)
    assert exc_info.value.code == "DEPARTMENT_ALREADY_INACTIVE"


def test_activating_an_already_active_department_is_rejected(services) -> None:
    department_service = services["department_service"]
    created = department_service.create_department(department_code="LC-GUARD-2", name="Guard Dept Two")

    with pytest.raises(ValidationError) as exc_info:
        department_service.activate_department(created.id)
    assert exc_info.value.code == "DEPARTMENT_ALREADY_ACTIVE"


def test_deactivate_department_records_distinct_activity_action(services) -> None:
    department_service = services["department_service"]
    activity_service = services["activity_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    created = department_service.create_department(department_code="LC-ACT-1", name="Activity Dept")
    department_service.deactivate_department(created.id)

    entries = activity_service.list_recent_for_entity("department", created.id, organization_id)
    actions = [entry.action for entry in entries]
    assert "department.deactivate" in actions
    assert "department.update" not in actions  # never the generic fallback for a lifecycle change

    deactivate_entry = next(entry for entry in entries if entry.action == "department.deactivate")
    assert "deactivated" in deactivate_entry.human_message.lower()


def test_activate_department_records_distinct_activity_action(services) -> None:
    department_service = services["department_service"]
    activity_service = services["activity_service"]
    organization_id = services["tenant_context_service"].get_active_organization().id

    created = department_service.create_department(department_code="LC-ACT-2", name="Activity Dept Two")
    department_service.deactivate_department(created.id)
    department_service.activate_department(created.id)

    entries = activity_service.list_recent_for_entity("department", created.id, organization_id)
    actions = [entry.action for entry in entries]
    assert "department.activate" in actions

    activate_entry = next(entry for entry in entries if entry.action == "department.activate")
    assert "activated" in activate_entry.human_message.lower()


def test_deactivating_a_department_does_not_delete_or_cascade_to_employees(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]

    created = department_service.create_department(department_code="LC-CASCADE", name="Cascade Dept")
    employee = employee_service.create_employee(
        employee_code="LC-CASCADE-E1", full_name="Cascade Employee", department_id=created.id
    )
    department_service.deactivate_department(created.id)

    reloaded_department = department_service.get_department(created.id)
    assert reloaded_department is not None
    assert reloaded_department.is_active is False

    reloaded_employee = employee_service.get_employee(employee.id)
    assert reloaded_employee is not None
    assert reloaded_employee.department_id == created.id


def test_inactive_department_remains_readable_in_full_listing(services) -> None:
    department_service = services["department_service"]
    created = department_service.create_department(department_code="LC-READABLE", name="Readable Dept")
    department_service.deactivate_department(created.id)

    names = [d.name for d in department_service.list_departments(active_only=None)]
    assert "Readable Dept" in names


# --------------------------------------------------------------------------
# Multi-level (transitive) parent-department cycle detection
# --------------------------------------------------------------------------


def test_department_with_no_parent_is_valid(services) -> None:
    department_service = services["department_service"]
    created = department_service.create_department(department_code="HIER-NONE", name="No Parent Dept")
    assert created.parent_department_id is None


def test_department_with_a_valid_parent_is_accepted(services) -> None:
    department_service = services["department_service"]
    parent = department_service.create_department(department_code="HIER-PARENT", name="Parent Dept")
    child = department_service.create_department(
        department_code="HIER-CHILD", name="Child Dept", parent_department_id=parent.id
    )
    assert child.parent_department_id == parent.id


def test_direct_self_parent_is_still_rejected(services) -> None:
    department_service = services["department_service"]
    department = department_service.create_department(department_code="HIER-SELF", name="Self Dept")
    with pytest.raises(ValidationError, match="cannot be its own parent"):
        department_service.update_department(
            department.id, parent_department_id=department.id, expected_version=department.version
        )


def test_two_node_cycle_is_rejected(services) -> None:
    """A -> B, then attempting B -> A."""
    department_service = services["department_service"]
    a = department_service.create_department(department_code="HIER-2A", name="A")
    b = department_service.create_department(department_code="HIER-2B", name="B", parent_department_id=a.id)

    with pytest.raises(ValidationError, match="cycle") as exc_info:
        department_service.update_department(a.id, parent_department_id=b.id, expected_version=a.version)
    assert exc_info.value.code == "DEPARTMENT_PARENT_CYCLE"


def test_three_level_cycle_is_rejected(services) -> None:
    """Chain: leaf.parent = mid, mid.parent = root (leaf -> mid -> root).
    Attempting to then set root's own parent to leaf would close the loop
    (root -> leaf -> mid -> root) -- rejected even though it's the ROOT
    being re-parented to a distant descendant, not a direct self-parent."""
    department_service = services["department_service"]
    root = department_service.create_department(department_code="HIER-3-ROOT", name="Root3")
    mid = department_service.create_department(department_code="HIER-3-MID", name="Mid3", parent_department_id=root.id)
    leaf = department_service.create_department(department_code="HIER-3-LEAF", name="Leaf3", parent_department_id=mid.id)

    with pytest.raises(ValidationError, match="cycle") as exc_info:
        department_service.update_department(root.id, parent_department_id=leaf.id, expected_version=root.version)
    assert exc_info.value.code == "DEPARTMENT_PARENT_CYCLE"


def test_deeper_cycle_is_rejected(services) -> None:
    """Chain: a (root, no parent) -> b -> c -> d -> e (each .parent points
    to the previous). Re-parenting b (not the true root a) to its own
    descendant e would close a b->c->d->e->b loop without touching a at
    all -- proving the walk checks the whole chain, not just the root."""
    department_service = services["department_service"]
    a = department_service.create_department(department_code="HIER-DEEP-A", name="DA")
    b = department_service.create_department(department_code="HIER-DEEP-B", name="DB", parent_department_id=a.id)
    c = department_service.create_department(department_code="HIER-DEEP-C", name="DC", parent_department_id=b.id)
    d = department_service.create_department(department_code="HIER-DEEP-D", name="DD", parent_department_id=c.id)
    e = department_service.create_department(department_code="HIER-DEEP-E", name="DE", parent_department_id=d.id)

    with pytest.raises(ValidationError, match="cycle") as exc_info:
        department_service.update_department(b.id, parent_department_id=e.id, expected_version=b.version)
    assert exc_info.value.code == "DEPARTMENT_PARENT_CYCLE"


def test_valid_deep_hierarchy_is_accepted(services) -> None:
    """A -> B -> C -> D, then re-pointing D at A is NOT a cycle (A has no
    parent), and must be accepted."""
    department_service = services["department_service"]
    a = department_service.create_department(department_code="HIER-VALID-A", name="VA")
    b = department_service.create_department(department_code="HIER-VALID-B", name="VB", parent_department_id=a.id)
    c = department_service.create_department(department_code="HIER-VALID-C", name="VC", parent_department_id=b.id)
    d = department_service.create_department(department_code="HIER-VALID-D", name="VD")

    updated = department_service.update_department(d.id, parent_department_id=c.id, expected_version=d.version)
    assert updated.parent_department_id == c.id


def test_cross_organization_parent_still_rejected_alongside_cycle_hardening(services) -> None:
    department_service = services["department_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = organization_service.create_organization(
        organization_code="HIER-CROSSORG", display_name="Other Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_parent = department_service.create_department(department_code="HIER-FOREIGN", name="Foreign")
    tenant_context_service.set_active_organization(default_organization.id)

    with pytest.raises(ValidationError, match="Parent department must belong to the active organization"):
        department_service.create_department(
            department_code="HIER-CROSSORG-CHILD", name="Child", parent_department_id=foreign_parent.id
        )


# --------------------------------------------------------------------------
# Head of Department (HOD): presenter payload mapping + read-model name
# resolution
# --------------------------------------------------------------------------


def test_create_department_with_head_of_department_via_presenter_payload(services) -> None:
    employee_service = services["employee_service"]
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    head_of_department = employee_service.create_employee(employee_code="HOD-1", full_name="Anna Mueller")

    result = admin.createDepartment({
        "departmentCode": "HOD-DEPT-1",
        "name": "Department With HOD",
        "headOfDepartmentEmployeeId": head_of_department.id,
    })
    assert result["ok"] is True

    catalog_result = admin.departments
    row = next(item for item in catalog_result["items"] if item["state"]["departmentCode"] == "HOD-DEPT-1")
    assert row["state"]["headOfDepartmentEmployeeId"] == head_of_department.id
    assert row["state"]["headOfDepartmentDisplay"] == "Anna Mueller"
    # Never a raw UUID standing in for the display name.
    assert row["state"]["headOfDepartmentDisplay"] != head_of_department.id


def test_update_department_head_of_department_via_presenter_payload(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    department = department_service.create_department(department_code="HOD-DEPT-2", name="Dept Two")
    head_of_department = employee_service.create_employee(employee_code="HOD-2", full_name="John Doe")

    result = admin.updateDepartment({
        "departmentId": department.id,
        "departmentCode": department.department_code,
        "name": department.name,
        "headOfDepartmentEmployeeId": head_of_department.id,
        "expectedVersion": department.version,
    })
    assert result["ok"] is True

    reloaded = department_service.get_department(department.id)
    assert reloaded.head_of_department_employee_id == head_of_department.id


def test_clear_department_head_of_department_via_presenter_payload(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    head_of_department = employee_service.create_employee(employee_code="HOD-3", full_name="Clear Me")
    department = department_service.create_department(
        department_code="HOD-DEPT-3", name="Dept Three", head_of_department_employee_id=head_of_department.id
    )
    assert department.head_of_department_employee_id == head_of_department.id

    result = admin.updateDepartment({
        "departmentId": department.id,
        "departmentCode": department.department_code,
        "name": department.name,
        "headOfDepartmentEmployeeId": "",
        "expectedVersion": department.version,
    })
    assert result["ok"] is True

    reloaded = department_service.get_department(department.id)
    assert reloaded.head_of_department_employee_id is None


def test_cross_organization_head_of_department_still_rejected(services) -> None:
    department_service = services["department_service"]
    employee_service = services["employee_service"]
    organization_service = services["organization_service"]
    tenant_context_service = services["tenant_context_service"]
    default_organization = tenant_context_service.get_active_organization()

    other_organization = organization_service.create_organization(
        organization_code="HOD-CROSSORG", display_name="Other Org", timezone_name="UTC", base_currency="USD"
    )
    tenant_context_service.set_active_organization(other_organization.id)
    foreign_employee = employee_service.create_employee(employee_code="HOD-FOREIGN", full_name="Foreign Head of Department")
    tenant_context_service.set_active_organization(default_organization.id)

    with pytest.raises(ValidationError, match="Department Head of Department must reference an existing employee"):
        department_service.create_department(
            department_code="HOD-CROSSORG-DEPT", name="Cross Org Dept", head_of_department_employee_id=foreign_employee.id
        )


def test_head_of_department_options_are_real_employee_names_scoped_to_active_organization(services) -> None:
    employee_service = services["employee_service"]
    registry = build_desktop_api_registry(services)
    catalog = PlatformWorkspaceCatalog(desktop_api_registry=registry)
    admin = catalog.adminWorkspace

    employee_service.create_employee(employee_code="HOD-OPT-1", full_name="Option Employee One")
    admin.refresh()

    options = admin.departmentEditorOptions["headOfDepartmentOptions"]
    labels = [option["label"] for option in options]
    assert "Option Employee One" in labels
    # Never a bare UUID standing in for a label.
    for option in options:
        assert option["label"] != option["value"]
