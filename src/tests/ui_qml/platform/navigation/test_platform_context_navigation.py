from __future__ import annotations

from src.ui_qml.platform.navigation.platform_context_navigation import (
    build_platform_context_navigation,
)


def _item_ids(view_model) -> set[str]:
    return {item.id for item in view_model.flat_items()}


def test_zero_permissions_still_shows_overview_only() -> None:
    view_model = build_platform_context_navigation(held_permissions=frozenset())
    assert _item_ids(view_model) == {"overview"}


def test_full_permission_set_shows_every_destination() -> None:
    all_permissions = frozenset(
        {
            "settings.manage",
            "site.read",
            "department.read",
            "employee.read",
            "party.read",
            "task.read",
            "auth.manage",
            "access.manage",
            "approval.request",
            "audit.read",
            "platform.admin",
        }
    )
    view_model = build_platform_context_navigation(held_permissions=all_permissions)
    ids = _item_ids(view_model)
    for expected in (
        "overview",
        "organizations",
        "sites",
        "departments",
        "employees",
        "parties",
        "calendars",
        "users",
        "access",
        "documents",
        "structures",
        "control_approvals",
        "control_audit",
        "settings",
        "tenants",
    ):
        assert expected in ids, expected


def test_destination_visible_when_any_one_required_permission_held() -> None:
    view_model = build_platform_context_navigation(held_permissions=frozenset({"site.read"}))
    assert "sites" in _item_ids(view_model)
    assert "organizations" not in _item_ids(view_model)  # requires settings.manage only


def test_groups_match_target_platform_context_tree() -> None:
    all_permissions = frozenset(
        {
            "settings.manage",
            "site.read",
            "department.read",
            "employee.read",
            "party.read",
            "task.read",
            "auth.manage",
            "access.manage",
            "approval.request",
            "audit.read",
            "platform.admin",
        }
    )
    view_model = build_platform_context_navigation(held_permissions=all_permissions)
    groups_by_id = {group.id: group for group in view_model.groups}

    assert {item.id for item in groups_by_id["organization"].items} == {
        "organizations",
        "sites",
        "departments",
        "employees",
        "parties",
        "calendars",
    }
    assert {item.id for item in groups_by_id["identity_access"].items} == {"users", "access"}
    assert {item.id for item in groups_by_id["documents"].items} == {"documents", "structures"}
    assert {item.id for item in groups_by_id["control"].items} == {"control_approvals", "control_audit"}
    assert {item.id for item in groups_by_id["administration"].items} == {"settings", "tenants"}
    assert {item.id for item in groups_by_id[""].items} == {"overview"}


def test_no_permission_codes_leak_into_serialized_qml_shape() -> None:
    view_model = build_platform_context_navigation(held_permissions=frozenset({"platform.admin"}))
    for group_dict in view_model.to_qml_groups():
        for item_dict in group_dict["items"]:
            assert set(item_dict.keys()) == {
                "id",
                "label",
                "iconKey",
                "routeId",
                "groupId",
                "order",
                "enabled",
            }


def test_roles_and_access_label_matches_page_title() -> None:
    view_model = build_platform_context_navigation(held_permissions=frozenset({"access.manage"}))
    access_item = next(item for item in view_model.flat_items() if item.id == "access")
    assert access_item.label == "Roles & Access"


def test_tenant_management_label_matches_page_title() -> None:
    view_model = build_platform_context_navigation(held_permissions=frozenset({"platform.admin"}))
    tenants_item = next(item for item in view_model.flat_items() if item.id == "tenants")
    assert tenants_item.label == "Tenant Management"
