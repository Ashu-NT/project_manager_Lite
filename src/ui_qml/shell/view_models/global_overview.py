from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SectionState:
    """Per-section presentation load state. Each Global Overview section
    (context, attention, modules, recent activity, action center, quick
    actions) tracks its own independently -- one section's failure never
    forces the others into an error or loading state."""

    loading: bool = False
    error_message: str | None = None
    empty: bool = False


@dataclass(frozen=True)
class GlobalOverviewContextViewModel:
    tenant_name: str
    organization_name: str
    role_label: str | None
    # Convenience display string built from the structured fields above,
    # joining only the non-empty parts with a middle-dot separator so it
    # never carries a dangling separator when role_label is None.
    context_line: str


@dataclass(frozen=True)
class AttentionCardViewModel:
    key: str
    label: str
    value: int
    supporting_text: str
    route_id: str
    filter_key: str


@dataclass(frozen=True)
class ActionCenterRowViewModel:
    id: str
    title: str
    module_label: str
    subject_display: str
    action_state: str
    status_label: str
    priority_label: str | None
    due_label: str | None
    route_id: str
    kind: str


@dataclass(frozen=True)
class ActivityRowViewModel:
    id: str
    title: str
    actor_label: str
    module_label: str
    timestamp_label: str
    icon: str | None
    color: str | None
    activity_type: str


@dataclass(frozen=True)
class ModuleCardViewModel:
    module_code: str
    title: str
    description: str
    icon_key: str
    summary_text: str
    route_id: str


@dataclass(frozen=True)
class QuickActionViewModel:
    key: str
    label: str
    icon: str
    route_id: str
    action_type: str = "navigate"


@dataclass(frozen=True)
class GlobalOverviewViewModel:
    """Conceptual aggregate of every Global Overview section. Not required by
    the controller (which tracks each section independently), but useful as
    a single-shot return type for tests and any future combined consumer."""

    context: GlobalOverviewContextViewModel | None
    attention: tuple[AttentionCardViewModel, ...] = field(default_factory=tuple)
    modules: tuple[ModuleCardViewModel, ...] = field(default_factory=tuple)
    recent_activity: tuple[ActivityRowViewModel, ...] = field(default_factory=tuple)
    action_center: tuple[ActionCenterRowViewModel, ...] = field(default_factory=tuple)
    quick_actions: tuple[QuickActionViewModel, ...] = field(default_factory=tuple)


def build_context_line(
    *,
    tenant_name: str,
    organization_name: str,
    role_label: str | None,
) -> str:
    parts = [part for part in (tenant_name, organization_name, role_label) if part]
    return " · ".join(parts)


__all__ = [
    "SectionState",
    "GlobalOverviewContextViewModel",
    "AttentionCardViewModel",
    "ActionCenterRowViewModel",
    "ActivityRowViewModel",
    "ModuleCardViewModel",
    "QuickActionViewModel",
    "GlobalOverviewViewModel",
    "build_context_line",
]
