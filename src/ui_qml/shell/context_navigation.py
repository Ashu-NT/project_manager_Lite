from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContextNavigationItemViewModel:
    """One leaf destination in a navigation tree."""

    id: str
    label: str
    icon_key: str
    route_id: str
    group_id: str
    order: int = 0
    enabled: bool = True


@dataclass(frozen=True)
class ContextNavigationGroupViewModel:
    """One expandable group of destinations. A group with `id == ""` is the
    ungrouped/root bucket -- always rendered expanded, never collapsible."""

    id: str
    label: str
    order: int = 0
    expanded_by_default: bool = True
    items: tuple[ContextNavigationItemViewModel, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ContextNavigationViewModel:
    """A full tree for one workspace (Platform, Project Management, ... or
    the shell-level Global tree, workspace_id="global")."""

    workspace_id: str
    title: str
    groups: tuple[ContextNavigationGroupViewModel, ...] = field(default_factory=tuple)

    def flat_items(self) -> tuple[ContextNavigationItemViewModel, ...]:
        return tuple(
            item
            for group in sorted(self.groups, key=lambda g: g.order)
            for item in sorted(group.items, key=lambda i: i.order)
        )

    def to_qml_groups(self) -> list[dict[str, object]]:
        """Serialize to the plain-dict shape QML/Property("QVariantList")
        consumes. No permission data or domain objects -- id/label/icon/
        route/order only."""
        return [
            {
                "id": group.id,
                "label": group.label,
                "order": group.order,
                "expandedByDefault": group.expanded_by_default,
                "items": [
                    {
                        "id": item.id,
                        "label": item.label,
                        "iconKey": item.icon_key,
                        "routeId": item.route_id,
                        "groupId": item.group_id,
                        "order": item.order,
                        "enabled": item.enabled,
                    }
                    for item in group.items
                ],
            }
            for group in sorted(self.groups, key=lambda g: g.order)
        ]


def resolve_safe_context_destination(
    current_id: str,
    tree: ContextNavigationViewModel,
    *,
    preferred_id: str = "",
) -> str:
    """Resolve a safe destination id for `tree`, given the currently-selected
    `current_id`. Returns `current_id` unchanged when it is still present in
    the tree. Otherwise prefers `preferred_id` when present, then falls back
    to the tree's first item in group/item order, then to `current_id`
    itself if the tree has no items at all."""
    items = tree.flat_items()
    available_ids = {item.id for item in items}
    if current_id in available_ids:
        return current_id
    if preferred_id and preferred_id in available_ids:
        return preferred_id
    return items[0].id if items else current_id


def build_context_navigation_view_model(
    *,
    workspace_id: str,
    title: str,
    groups: list[ContextNavigationGroupViewModel],
) -> ContextNavigationViewModel:
    return ContextNavigationViewModel(
        workspace_id=workspace_id,
        title=title,
        groups=tuple(groups),
    )


__all__ = [
    "ContextNavigationItemViewModel",
    "ContextNavigationGroupViewModel",
    "ContextNavigationViewModel",
    "build_context_navigation_view_model",
    "resolve_safe_context_destination",
]
