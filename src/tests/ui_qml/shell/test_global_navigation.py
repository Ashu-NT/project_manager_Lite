from __future__ import annotations

from src.ui_qml.shell.global_navigation import build_global_navigation_tree
from src.ui_qml.shell.navigation import NavigationItemViewModel, filter_navigation_items


def _item(route_id: str, module_code: str, title: str) -> NavigationItemViewModel:
    return NavigationItemViewModel(
        route_id=route_id,
        module_code=module_code,
        module_label=module_code,
        group_label="",
        title=title,
        qml_source="file:///dummy.qml",
    )


_ALL_ITEMS = [
    _item("shell.home", "shell", "Overview"),
    _item("platform.workspace", "platform", "Platform"),
    _item("project_management.workspace", "project_management", "Project Management"),
]


def test_overview_is_ungrouped_root_item() -> None:
    tree = build_global_navigation_tree(_ALL_ITEMS)
    root_group = next(group for group in tree.groups if group.id == "")
    assert [item.label for item in root_group.items] == ["Overview"]


def test_platform_is_administration_and_pm_is_business() -> None:
    tree = build_global_navigation_tree(_ALL_ITEMS)
    groups_by_id = {group.id: group for group in tree.groups}
    assert [item.label for item in groups_by_id["administration"].items] == ["Platform"]
    assert [item.label for item in groups_by_id["business"].items] == ["Project Management"]


def test_pm_dropped_when_filtered_out_by_module_accessibility() -> None:
    accessible_items = filter_navigation_items(_ALL_ITEMS, accessible_module_codes=frozenset())
    tree = build_global_navigation_tree(accessible_items)
    groups_by_id = {group.id: group for group in tree.groups}
    assert "business" not in groups_by_id
    assert [item.label for item in groups_by_id["administration"].items] == ["Platform"]


def test_no_unmapped_module_codes_render_a_fake_group() -> None:
    items = [*_ALL_ITEMS, _item("inventory.workspace", "inventory", "Inventory")]
    tree = build_global_navigation_tree(items)
    all_labels = {item.label for group in tree.groups for item in group.items}
    assert "Inventory" not in all_labels
